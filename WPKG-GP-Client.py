# -*- encoding: utf-8 -*-
import wx
from wx.lib.delayedresult import startWorker
# Imports WPKGCOnnection:
from win32pipe import *
from win32file import *
import pywintypes
import win32api
#import winerror
import load_config
from utilities import *
from help import HelpDialog
from img import AppImages

# set translation function
_ = wx.GetTranslation
#if you are getting unicode errors, try something like:
#_ = lambda s: wx.GetTranslation(s).encode('utf-8')

# get program path
path = get_client_path()

# load Image class
img = AppImages(path)

# set path to wpkg.xml and get system architecture
xml_file, arch = get_wpkg_db()

# Loading and setting INI settings:
# ---------------------------------
try:
    ini = load_config.ConfigIni(os.path.join(path, 'wpkg-gp_client.ini'))
except load_config.NoConfigFile, error_msg:
    # Config file could not be opened!
    print error_msg
    no_config = True
else:
    no_config = False
    # General
    allow_quit = ini.loadsetting('General', 'allow quit')
    check_last_upgrade = ini.loadsetting('General', 'check last update')
    last_upgrade_interval = ini.loadsetting('General', 'last update interval')
    if not isinstance(last_upgrade_interval, (int, long)):
        last_upgrade_interval = 14
    check_vpn = ini.loadsetting('General', 'check vpn')
    shutdown_timeout = ini.loadsetting('General', 'shutdown timeout')
    if not isinstance(shutdown_timeout, (int, long)):
        shutdown_timeout = 30
    help_file = ini.loadsetting('General', 'help file')
    # Update Check
    update_startup = ini.loadsetting('Update Check', 'startup')
    update_interval = ini.loadsetting('Update Check', 'interval')
    if isinstance(update_interval, (int, long)):
        # Transform Minutes to Milliseconds for wx.python timer
        update_interval = update_interval * 60 * 1000
    else:
        update_interval = False
    update_url = ini.loadsetting('Update Check', 'update url')
    check_bootup_log = ini.loadsetting('General', 'check boot log')


def create_menu_item(menu, label, image, func):
    item = wx.MenuItem(menu, -1, label)
    item.SetBitmap(img.get(image))
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.AppendItem(item)
    return item


class TaskBarIcon(wx.TaskBarIcon):
    def __init__(self, trayicon, tooltip):
        super(TaskBarIcon, self).__init__()
        self.show_no_updates = False

        # Set trayicon and tooltip
        icon = wx.IconFromBitmap(wx.Bitmap(trayicon))
        self.SetIcon(icon, tooltip)

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
            try:
                reboot_pending = ReadRebootPendingTime()
            except WindowsError:
                dlg_title = _(u'Registry Error')
                dlg_msg = _(u'No access to necessary registry key.')
                dlg = wx.MessageDialog(None, dlg_msg, dlg_title, wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()
                return
            if reboot_pending and reboot_pending > self.bootup_time:
                dlg_msg = _(u"Reboot required!\n\n"
                           u"A reboot is required before the system\n"
                           u"can be updated again.\n"
                           u"Reboot now?")
                dlg = wx.MessageDialog(None, dlg_msg, _(u"Reboot required"),
                                       wx.YES_NO | wx.YES_DEFAULT | wx.ICON_EXCLAMATION)
                if dlg.ShowModal() == wx.ID_YES:
                    # Initiate Reboot
                    shutdown(1, time=5, msg=_(u"System will reboot now!"))
                    # Reset Reboot Pending
                    SetRebootPendingTime(reset=True)
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
        helpfile = os.path.join(path + help_file)
        helpdlg = HelpDialog(helpfile, title=_(u'WPKG-GP Client - Help'))
        helpdlg.Center()
        helpdlg.ShowModal()

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
        size_y = self.GetEffectiveMinSize()[1]
        #self.SetSize(size)
        self.SetSize((410, size_y))
        #self.SetSize((410, 273))

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
                out_msg = 'WPKG process start canceled by user.'
                self.update_box.SetValue(out_msg)
                return True, None
        # LONG TASK is the PipeConnection to the WPKG-GP Windows Service
        self.running = True
        #msg = 'Execute'
        msg = 'ExecuteNoReboot'
        #msg = "DUMDI"
        try:
            pipeHandle = CreateFile("\\\\.\\pipe\\WPKG", GENERIC_READ|GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
        except pywintypes.error, (n, f, e):
            #print "Error when generating pipe handle: %s" % e
            out_msg = u"Error: WPKG-GP Service not running"
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

                if out.startswith('Error') or out.startswith('Info'):
                    out_msg = out
                    self.shouldAbort = True
                    # TODO: ADD - You are not authorized to run wpkg

            except win32api.error as exc:
                if exc.winerror == winerror.ERROR_PIPE_BUSY:
                    win32api.Sleep(5000)
                    print 'Pipe Busy Error'
                    continue
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
                dlg_title = _(u"WPKG-GP Notification")
                dlg_icon = wx.ICON_INFORMATION
                if message.startswith("Error: Con"):
                    dlg_msg = _(u"The update server could not be reached.")
                    dlg_icon = wx.ICON_ERROR
                elif message.startswith("Error: WP"):
                    dlg_msg = _(u"Can't connect to the wpkg-gp service.")
                    dlg_icon = wx.ICON_ERROR
                elif message.startswith("Info: Cli"):
                    dlg_msg = _(u"The system was rejected from the server to execute an update!\n"
                                u"Contact your IT department for further information.")
                elif message.startswith(u"Info: You are not"):
                    dlg_msg = _(u"You are not authorized to execute a wpkg update!\n"
                                u"Contact your IT department for further information.")
                else:
                    dlg_msg = _(u'Unknown problem occured.')
                dlg = wx.MessageDialog(self, dlg_msg, dlg_title, wx.OK | dlg_icon)
                dlg.ShowModal()
            else:
                self.update_box.SetValue('WPKG Process Aborted.')
        else:
            if reboot:
                self.update_box.SetValue('WPKG process Finished, restart Necessary!')
            else:
                self.update_box.SetValue('WPKG process finished.')
        if error_log:
            log_dlg = ViewLogDialog(title=_(u"Error detected during update"), log=error_log)
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
                shutdown(1, time=shutdown_timeout, msg=_(u'System will reboot in %TIME% seconds.'))
                self.reboot_scheduled = True
                self.Close()
            else:
                # Reboot is Pending
                SetRebootPendingTime()
        elif reboot or chk_shutdown and not aborted:
            # TODO: DEBUG DIALOG INFO
            shutdown(2, time=shutdown_timeout, msg=_(u'System will shutdown in %TIME% seconds.'))
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


if __name__ == '__main__':
    app = wx.App(False)
    # Translation configuration
    localedir = os.path.join(path, "locale")
    mylocale = wx.Locale()
    # mylocale = wx.Locale(wx.LANGUAGE_SPANISH)
    # Add config option or settings to force language?
    mylocale.AddCatalogLookupPathPrefix(localedir)
    mylocale.AddCatalog('wpkg-gp-client')

    # If config file could not be opened
    if no_config:
        dlgmsg = _(u'Can\'t open config file "{}"!').format("wpkg-gp_client.ini")
        dlg = wx.MessageDialog(None, dlgmsg, "WPKG-GP Client", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        exit(1)

    # If an instance of WPKG-GP Client is running already in the users session
    if client_running():
        dlgmsg = _(u"An instance of WPKG-GP Client is already running!")
        dlg = wx.MessageDialog(None, dlgmsg, "WPKG-GP Client", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        exit()

    TRAY_TOOLTIP = 'WPKG-GP Client'
    TRAY_ICON = os.path.join(path, 'img', 'apacheconf-16.png')
    TaskBarIcon(trayicon=TRAY_ICON, tooltip=TRAY_TOOLTIP)
    app.MainLoop()

