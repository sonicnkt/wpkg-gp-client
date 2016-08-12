# -*- encoding: utf-8 -*-
import wx
from wx.lib.delayedresult import startWorker
# Imports WPKGCOnnection:
from win32pipe import *
from win32file import *
import pywintypes
import win32api
#import winerror
from utilities import *
from help import HelpDialog
from img import app_images

# Trasnlation Function
_ = wx.GetTranslation
#if you are getting unicode errors, try something like:
#_ = lambda s: wx.GetTranslation(s).encode('utf-8')

TRAY_TOOLTIP = 'WPKG-GP CLient'
TRAY_ICON = os.path.join(path,'img', 'apacheconf-16.png')
VERSION = "0.9.4"

# Detect if x86 or AMD64 and set correct path to wpkg.xml
# The Environment Variable PROCESSOR_ARCHITEW6432 only exists on 64bit Windows
if os.environ.get("PROCESSOR_ARCHITEW6432"):
    # Sysnative is needed to access the true System32 folder from a 32bit application (This Python Program)
    sys_folder = "Sysnative"
    arch = "x64"
else:
    sys_folder = "System32"
    arch = "x86"
xml_file = os.path.join(os.getenv('systemroot'), sys_folder, "wpkg.xml")


# Loading and Configuring INI Settings:
# -------------------------------------

allow_quit = LoadSetting('General', 'allow quit')
# Last Update Check
check_last_upgrade = LoadSetting('General', 'check last update')
last_upgrade_interval = LoadSetting('General', 'last update interval')
if not isinstance(last_upgrade_interval, (int, long)):
    last_upgrade_interval = 14
check_vpn = LoadSetting('General', 'check vpn')

update_startup = LoadSetting('Update Check', 'startup')
update_interval = LoadSetting('Update Check', 'interval')
if isinstance(update_interval, (int, long)):
    # Transform Minutes to Milliseconds
    update_interval = update_interval * 60 * 1000
else:
    update_interval = False
update_url = LoadSetting('Update Check', 'update url')
check_bootup_log = LoadSetting('General', 'check boot log')

# Load Image Class
img = app_images(path)


def create_menu_item(menu, label, image, func):
    item = wx.MenuItem(menu, -1, label)
    item.SetBitmap(img.get(image))
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.AppendItem(item)
    return item


class TaskBarIcon(wx.TaskBarIcon):
    def __init__(self):
        super(TaskBarIcon, self).__init__()
        self.show_no_updates = False
        self.set_icon(TRAY_ICON)
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.on_upgrade)
        self.Bind(wx.EVT_TASKBAR_BALLOON_CLICK, self.on_bubble)
        self.upd_error_count = 0
        self.updates_available = False
        self.shutdown_scheduled = False
        self.reboot_scheduled = False
        self.bootup_time = getBootUp()
        if update_interval:
            self.timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
            self.timer.Start(update_interval)
            if update_startup:
                self.on_timer(None)
        if check_bootup_log:
            last_check = check_file_date(xml_file)
            now = datetime.datetime.now()
            if (self.bootup_time + datetime.timedelta(hours=1) > now) and \
               (self.bootup_time + datetime.timedelta(minutes=30) > last_check):
                log, errorlog, reboot = check_eventlog(self.bootup_time)
                if errorlog:
                    error_str = _(u"Update error detected\n"
                                  u"during system start up.")
                    self.ShowBalloon(title=_(u'WPKG Error'), text=error_str, msec=100, flags=wx.ICON_ERROR)
                    title = _(u"System start error")
                    dlg = ViewLogDialog(title=title,log=errorlog)
                    dlg.ShowModal()
        if check_last_upgrade:
            # Check if the last changes to the local wpkg.xml are older than a specific time
            # Inform USER that he should upgrade the System
            last_check = check_file_date(xml_file)
            if last_check < (datetime.datetime.now() - datetime.timedelta(days=last_upgrade_interval)):
                dlg_str = _(u"System should be updated!\n\n"
                            u"System wasn't updated in over {} days.").format(str(last_upgrade_interval))
                dlg = wx.MessageDialog(None, dlg_str, _(u"Attention!"), wx.OK | wx.ICON_EXCLAMATION)
                dlg.ShowModal()
                self.on_upgrade(None)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        if update_interval:
            create_menu_item(menu, _(u"Check for updates"), "update", self.manual_timer)
        create_menu_item(menu, _(u"System update"), "upgrade", self.on_upgrade)
        menu.AppendSeparator()
        create_menu_item(menu, _(u"Help"), "help", self.on_about)
        if self.shutdown_scheduled:
            menu.AppendSeparator()
            create_menu_item(menu, _(u"Cancel shutdown"), "cancel", self.on_cancleshutdown)
        if allow_quit:
            menu.AppendSeparator()
            create_menu_item(menu, _(u"Close"), "quit", self.on_exit)
        return menu

    def set_icon(self, path):
        icon = wx.IconFromBitmap(wx.Bitmap(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def manual_timer(self, evt):
        self.show_no_updates = True
        self.on_timer(evt)

    def on_timer(self, evt):
        startWorker(self.update_check_done, self.update_check)

    def update_check(self):
        print 'Checking for Updates... ' + str(datetime.datetime.now()) #TODO: MOVE TO DEBUG LOGGER
        local_packages = get_local_packages(xml_file)
        remote_packages, e = get_remote_packages(update_url)
        if e:
            return str(e)
        return version_compare(local_packages, remote_packages)

    def update_check_done(self, result):
        r = result.get()
        print 'Update Check Done!' #TODO: MOVE TO DEBUG LOGGER
        if isinstance(r, basestring):
            # Error returned
            self.updates_available = False
            if self.upd_error_count < 2 and not self.show_no_updates:
                self.upd_error_count += 1
                print "Update Error: {}".format(self.upd_error_count) #TODO: MOVE TO DEBUG LOGGER
            else:
                error_str = _(u"Could not load update file:") + "\n" + r
                self.ShowBalloon(title=_(u'Update Error'), text=error_str, msec=100, flags=wx.ICON_ERROR)
                self.upd_error_count = 0
        elif r:
            # Updates Found
            self.updates_available = True
            text = ''
            for entry in r:
                text = text + entry[0] + ' - ver. ' + entry[1] + '\n'
            self.ShowBalloon(title=_(u"Update(s) available:"), text=text, msec=100, flags=wx.ICON_INFORMATION)
        else:
            # No Updates Found
            self.updates_available = False
            if self.show_no_updates:
                self.ShowBalloon(title=_(u"No Updates"), text=" ", msec=100, flags=wx.ICON_INFORMATION)
                self.show_no_updates = False

    def on_bubble(self, event):
        if self.updates_available:
            self.on_upgrade(None)

    def on_upgrade(self, event):
        try:
            if self.wpkg_dialog.IsShown():
                # If Dialog is opened allready raise window to top
                self.wpkg_dialog.Raise()
                return
        except:
            # Dialog is not opened yet
            # Check if Reboot is Pending
            reboot_pending = ReadRebootPendingTime()
            if reboot_pending and reboot_pending > self.bootup_time:
                dlgmsg = _(u"Reboot required!\n\n"
                           u"A reboot is required before the system\n"
                           u"can be updated again.\n"
                           u"Reboot now?")
                dlg = wx.MessageDialog(None, dlgmsg, _(u"Reboot required"),
                                       wx.YES_NO | wx.YES_DEFAULT | wx.ICON_EXCLAMATION)
                if dlg.ShowModal() == wx.ID_YES:
                    # Initiate Shutdown
                    shutdown(1, time=5, msg=_(u"System will reboot now!"))
                    # Reset Reboot Pending
                    SetRebootPendingTime(reset=True)
                    exit()
                    return
                else:
                    return
            elif reboot_pending:
                SetRebootPendingTime(reset=True)
            if update_interval:
                self.timer.Stop()
            self.wpkg_dialog = RunWPKGDialog(title=_(u'System Update'))
            self.wpkg_dialog.ShowModal()
            if self.wpkg_dialog.shutdown_scheduled == True:
                # Shutdown Scheduled add Cancel Option to Popup Menu
                self.shutdown_scheduled = True
            if self.wpkg_dialog.reboot_scheduled == True:
                # Reboot Scheduled add Cancel Option to Popup Menu
                self.shutdown_scheduled = True
                self.reboot_scheduled = True
            self.wpkg_dialog.Destroy()
            if update_interval:
                self.timer.Start()

    def on_about(self, evt):
        helpfile = os.path.join(path + 'help.html')
        helpdlg = HelpDialog(helpfile, title=_(u'WPKG-GP Client - Help'))
        helpdlg.Center()
        helpdlg.ShowModal()
        #info = wx.AboutDialogInfo()
        #info.Name = "WPKG-GP Client"
        #info.Version = VERSION
        #info.Copyright = "(C) 2016 Nils Thiele"
        #info.Description = u"WPKG-GP Client ist ein GUI Tool für den WPKG-GP Service\n" \
        #                   u"geschrieben in Python/wxPython"
        ## info.WebSite = ("http://www.pythonlibrary.org", "My Home Page")
        #info.Developers = ["Nils Thiele"]
        #info.License = "Completely and totally open source!"
        ## Show the wx.AboutBox
        #wx.AboutBox(info)

    def on_cancleshutdown(self, event):
        if self.reboot_scheduled:
            # If reboot is cancled, set rebootpendingtime to registry
            SetRebootPendingTime()
        shutdown(3) # Cancel Shutdown
        self.reboot_scheduled = False
        self.shutdown_scheduled = False

    def on_exit(self, event):
        try:
            if self.wpkg_dialog.IsShown():
                # Raise window to top
                self.wpkg_dialog.Raise()
                return
        except:
            self.Destroy()

class RunWPKGDialog(wx.Dialog):
    def __init__(self, title='Temp'):
        """Constructor"""
        wx.Dialog.__init__(self, None, title=title)

        self.shouldAbort = False
        self.running = False
        self.wpkg_start_time = None
        self.shutdown_scheduled = False
        self.reboot_scheduled = False
        self.log = ""
        self.InitUI()
        self.SetSize((410, 273))

    def InitUI(self):

        self.panel = wx.Panel(self, wx.ID_ANY)

        # Info Text
        infotext = _(u'Close all open Applications, it is possible that programs will be closed without a warning '
                     u'and system could reboot without further confirmation.')

        infobox = wx.StaticBox(self.panel, -1, _(u'Attention'))
        infoboxbsizer = wx.StaticBoxSizer(infobox, wx.VERTICAL)
        info = wx.StaticText(self.panel, label=infotext)
        info.Wrap(380)
        infoboxbsizer.Add(info, 0)

        self.gauge = wx.Gauge(self.panel, size=(24, 26))
        self.update_label = wx.StaticText(self.panel, label=_(u'Current Progress:'))
        self.update_box = wx.TextCtrl(self.panel, style=wx.TE_READONLY)
        self.update_box.SetBackgroundColour(wx.WHITE)
        self.chk_shutdown = wx.CheckBox(self.panel, size=(160,20), label=_(u"Shutdown after update"))

        self.logButton = wx.Button(self.panel, size=(54,26), label="LOG")
        self.logButton.SetToolTip(wx.ToolTip(_(u'Open WPKG Log')))
        self.logButton.SetBitmap(img.get('log'))
        self.startButton = wx.Button(self.panel, label=_(u"Update"))
        self.abortButton = wx.Button(self.panel, label=_(u"Cancel"))
        self.logButton.Disable()
        self.abortButton.Disable()

        self.line = wx.StaticLine(self.panel, -1, size=(2,2), style=wx.LI_HORIZONTAL)
        self.startButton.Bind(wx.EVT_BUTTON, self.OnStartButton)
        self.abortButton.Bind(wx.EVT_BUTTON, self.OnAbortButton)
        self.logButton.Bind(wx.EVT_BUTTON, self.OnLogButton)

        #self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(infoboxbsizer, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.gauge, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.update_label, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.update_box, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.line, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.chk_shutdown, 0, wx.LEFT | wx.EXPAND, 7)
        self.sizer2.Add(self.logButton, 0)
        self.sizer2.AddStretchSpacer()
        self.sizer2.Add(self.startButton, 0)#, wx.RIGHT, 2)
        self.sizer2.Add(self.abortButton, 0)
        self.sizer.Add(self.sizer2, 0, wx.ALL | wx.EXPAND, 5)
        self.panel.SetSizerAndFit(self.sizer)
        self.Center()

    def OnStartButton(self, e):
        dlg_title = _(u"2. Warning")
        dlg_msg = _(u"Close all open programs!\n\nThe System could restart without further confirmation!\n\n" \
                    u"Continue?")
        dlg = wx.MessageDialog(self, dlg_msg, dlg_title, wx.YES_NO|wx.YES_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            dlg.Destroy()
            # Deactivate Buttons and Close Window option!
            self.startButton.Disable()
            self.abortButton.Enable()
            self.EnableCloseButton(enable=False)
            # Set Start Time
            self.wpkg_start_time = datetime.datetime.now()
            # Reset Log
            self.log = None
            startWorker(self.LongTaskDone, self.LongTask)

    def OnAbortButton(self, e):
        if not self.running:
            self.Close()
            return
        dlg_title = _(u"Cancel")
        dlg_msg = _(u"System update in progress!\n\n Canceling this Progress could result in installation issues.\n"
                    u"Cancel?")
        dlg = wx.MessageDialog(self, dlg_msg, dlg_title, wx.YES_NO|wx.YES_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            dlg.Destroy()
            if not self.running:
                print 'WPKG Process finished, no abort possible' #TODO: MOVE TO DEBUG LOGGER
                return
            print 'Aborting WPKG Process' #TODO: MOVE TO DEBUG LOGGER
            self.shouldAbort = True
            msg = 'Cancel'
            try:
                pipeHandle = CreateFile("\\\\.\\pipe\\WPKG", GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
            except pywintypes.error, (n, f, e):
                print "Error when generating pipe handle: %s" % e #TODO: MOVE TO DEBUG LOGGER
                return 1

            SetNamedPipeHandleState(pipeHandle, PIPE_READMODE_MESSAGE, None, None)
            WriteFile(pipeHandle, msg)


    def LongTask(self):
        # Checking if System is connected through VPN
        out_msg = None
        if check_vpn and vpn_connected(arch=arch):
            dlg_title = _(u"Attention")
            dlg_msg = _(u"System detected a active VPN Connection using Cisco Anyconnect\n"
                        u"This could result in slow upgrade progress and updates for the AnyConnect\n"
                        u"Software will be blocked.\n"
                        u"Continue?")
            dlg = wx.MessageDialog(self, dlg_msg, dlg_title, wx.YES_NO | wx.YES_DEFAULT | wx.ICON_INFORMATION)
            if dlg.ShowModal() == wx.ID_NO:
                # Return Abort True
                out_msg = 'Process Start canceled by user!'
                return True, out_msg
        # LONG TASK is the PipeConnection to the WPKG-GP Windows Service
        self.running = True
        #msg = 'Execute'
        msg = 'ExecuteNoReboot'
        #msg = "DUMDI"
        try:
            pipeHandle = CreateFile("\\\\.\\pipe\\WPKG", GENERIC_READ|GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
        except pywintypes.error, (n, f, e):
            #print "Error when generating pipe handle: %s" % e
            out_msg = u"Error: WPKG-GP Service nicht verfügbar."
            return True, out_msg

        SetNamedPipeHandleState(pipeHandle, PIPE_READMODE_MESSAGE, None, None)
        WriteFile(pipeHandle, msg)
        while 1:
            try:
                (hr, readmsg) = ReadFile(pipeHandle, 512)
                out = readmsg[4:] #Strip 3 digit status code
                self.update_box.SetValue(out)
                percentage = getPercentage(out)
                wx.CallAfter(self.gauge.SetValue, percentage)
                print out
                if out.startswith("Error"):
                    out_msg = out
                    self.shouldAbort = True
            except win32api.error as exc:
                if exc.winerror == winerror.ERROR_PIPE_BUSY:
                    win32api.Sleep(5000)
                    print 'Pipe Busy Error'
                    continue
                # WPKG PROCESS FINISHED
                break

        return self.shouldAbort, out_msg

    def LongTaskDone(self, result):
        self.running = False
        self.chk_shutdown.Disable()
        chk_shutdown = self.chk_shutdown.IsChecked()
        self.gauge.SetValue(100)
        aborted, message = result.get()
        # TODO: Change Reboot Detection?
        self.log, error_log, reboot = check_eventlog(self.wpkg_start_time)
        if aborted: # or message:
            # PROCESS ABORTED OR PROBLEMS
            self.chk_shutdown.SetValue(False)
            if message:
                self.update_box.SetValue(message)
                dlg_title = _(u"Connection error")
                dlg_msg = ''
                if message.startswith("Error: Con"):
                    dlg_msg = _(u"The update server could not be reached!")
                if message.startswith("Error: Cli"):
                    dlg_msg = _(u"The system was rejected from the server to execute an update!\n"
                                u"Contact your IT department for further information")

                dlg = wx.MessageDialog(self, dlg_msg, dlg_title, wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
            else:
                self.update_box.SetValue('WPKG Process Aborted.')
        else:
            if reboot:
                self.update_box.SetValue('WPKG process Finished, restart Necessary!')
            else:
                self.update_box.SetValue('WPKG process finished.')
        if error_log:
            log_dlg = ViewLogDialog(title="Fehler bei der Aktualisierung", log=error_log)
            log_dlg.ShowModal()
            log_dlg.Destroy()
        if reboot and not chk_shutdown and not aborted:
            dlg_title = _(u"Reboot required")
            dlg_msg = _(u"Reboot required!\n\n"
                        u"For the completion of the installation(s), a reboot is required.\n"
                        u"Reboot now?")
            dlg = wx.MessageDialog(self, dlg_msg, dlg_title, wx.YES_NO | wx.YES_DEFAULT | wx.ICON_EXCLAMATION)
            if dlg.ShowModal() == wx.ID_YES:
                # Initiate Shutdown
                shutdown(1, time=20, msg=_(u'System will reboot in %TIME% seconds.'))
                self.reboot_scheduled = True
                self.Close()
            else:
                # Reboot is Pending
                SetRebootPendingTime()
        elif reboot or chk_shutdown and not aborted:
            # TODO: DEBUG DIALOG INFO
            shutdown(2, msg=_(u'System will shutdown in %TIME% seconds.'))
            if reboot:
                self.reboot_scheduled = True
            else:
                self.shutdown_scheduled = True
            self.Close()
        if not self.log:
            self.log.append(_(u"No System changes."))
        self.logButton.Enable()
        self.abortButton.SetLabel(_(u'Close'))
        self.shouldAbort = False
        self.EnableCloseButton(enable=True)

    def OnLogButton(self, evt):
        logdlg = ViewLogDialog(title='WPKG Log - {}'.format(self.wpkg_start_time.strftime("%Y/%m/%d %H:%M:%S")),
                               log=self.log)
        logdlg.ShowModal()


class ViewLogDialog(wx.Dialog):
    def __init__(self, title='Temp', log="Temp"):
        """Constructor"""
        wx.Dialog.__init__(self, None, title=title, style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.log = "\n".join(log)

        self.InitUI()
        self.SetSize((640, 480))


    def InitUI(self):

        self.panel = wx.Panel(self, wx.ID_ANY)
        self.textbox = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.textbox.SetValue(self.log)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.textbox, 1, wx.ALL | wx.EXPAND, 5)
        self.panel.SetSizerAndFit(self.sizer)
        self.Center()

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, evt):
        self.Destroy()


def main():
    app = wx.App(False)
    # Translation Configuration
    localedir = os.path.join(path, "locale")
    mylocale = wx.Locale()
    # Forcing any language to wx.Locale() results in changes of the win32evtlog time format and breaking the parser!
    mylocale.AddCatalogLookupPathPrefix(localedir)
    mylocale.AddCatalog('wpkg-gp-client')
    if client_running():
        dlgmsg = _(u"An instance of WPKG-GP Client is allready running!")
        dlg = wx.MessageDialog(None, dlgmsg, "WPKG-GP Client", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        return
    TaskBarIcon()
    app.MainLoop()

if __name__ == '__main__':
    main()