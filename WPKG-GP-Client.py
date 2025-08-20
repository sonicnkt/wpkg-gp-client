# -*- encoding: utf-8 -*-
import webbrowser

import wx
from wx.lib.delayedresult import startWorker
from wx.adv import TaskBarIcon as TaskBarIcon
import load_config
from utilities import *
from help import HelpDialog
from img import AppImages

# set translation function
_ = wx.GetTranslation
#if you are getting unicode errors, try something like:
#_ = lambda s: wx.GetTranslation(s).encode('utf-8')


# Get  directory paths
client_path, bundle_path = get_paths()
print("Client Path: ", client_path)
print("Bundle Path: ", bundle_path)

# load Image class
img = AppImages(bundle_path)

# set path to wpkg.xml and get system architecture
xml_file, arch = check_system_architecture()

req_wpkggp_ver = '0.17.17'
app_name = 'WPKG-GP Client'

#Change working directory to get relative paths working for the images in the help files:
os.chdir(client_path)

# Loading and setting INI settings:
# ---------------------------------
try:
    ini = load_config.ConfigIni(os.path.join(client_path, 'wpkg-gp_client.ini'))
except load_config.NoConfigFile as error_msg:
    # Config file could not be opened!
    print(error_msg)
    no_config = True
else:
    no_config = False
    # General
    allow_quit = ini.load_setting('General', 'allow quit', bool, False)
    check_last_upgrade = ini.load_setting('General', 'check last update', bool, False)
    last_upgrade_interval = ini.load_setting('General', 'last update interval', int, 14)
    is_it_department_website_button_active = ini.load_setting('General', 'show it department website button',
                                                              bool, False)
    it_department_website = ini.load_setting('General', 'it department website', str, 'https://example.com')
    check_vpn = ini.load_setting('General', 'check vpn', bool, False)
    shutdown_timeout = ini.load_setting('General', 'shutdown timeout', int, 30)
    help_file = ini.load_setting('General', 'help file', str, '')
    # Update Check method
    update_method = ini.load_setting('Update Check', 'method', str, 'wpkg-gp')
    if update_method not in ['wpkg-gp', 'updatefile'] and update_method != False:
        update_method = 'wpkg-gp'
    # Update Check filter
    raw_update_filter = ini.load_setting('Update Check', 'filter')
    available_filter = ('update', 'install', 'downgrade', 'remove')
    if isinstance(raw_update_filter, str) and (raw_update_filter != ''):
        raw_update_filter = raw_update_filter.lower().strip().split(';')
        update_filter = tuple([entry for entry in raw_update_filter if entry in available_filter])
    else:
        update_filter = None
    if not update_filter:
        update_filter = available_filter
    print("Update Filters: ", repr(update_filter))
    # Update Check blacklist
    raw_update_blacklist = ini.load_setting('Update Check', 'blacklist')
    if isinstance(raw_update_blacklist, str) and (raw_update_blacklist != ''):
        update_blacklist = tuple(raw_update_blacklist.lower().strip().split(';'))
    else:
        update_blacklist = ()
    update_startup = ini.load_setting('Update Check', 'startup', bool, False)
    update_interval = ini.load_setting('Update Check', 'interval', int, 30)
    if isinstance(update_interval, int):
        # Transform Minutes to Milliseconds for wx.python timer
        update_interval = update_interval * 60 * 1000
    else:
        update_interval = False
    update_url = ini.load_setting('Update Check', 'update url', str, '')
    check_bootup_log = ini.load_setting('General', 'check boot log', bool, False)


def create_menu_item(menu: wx.Menu, label: str, image: str, func: callable):
    """
        Create a wx.MenuItem, add an icon if available, bind it to a handler, and append it to the menu.

        Args:
            menu (wx.Menu): The wx.Menu to which the item will be added.
            label (str): The menu item's text label.
            image (str): Key for the image in the image_dict.
            func (callable): The event handler function for the menu item.

        Returns:
            wx.MenuItem: The newly created (and appended) menu item.
        """
    # Create the menu item
    item = wx.MenuItem(menu, -1, label)

    # Set bitmap if available for given key
    item.SetBitmap(img.get(image))

    # Bind the menu event to the handler function
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())

    # Append the item to the menu using the modern API
    menu.Append(item)
    return item


class TaskBarIcon(TaskBarIcon):
    def __init__(self, trayicon, tooltip):
        super(TaskBarIcon, self).__init__()
        self.show_no_updates = False

        # Create an icon from the provided bitmap
        icon = wx.Icon()
        icon.CopyFromBitmap(wx.Bitmap(trayicon))
        self.SetIcon(icon, tooltip)

        # Bind event handlers
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.on_upgrade)
        self.Bind(wx.adv.EVT_TASKBAR_BALLOON_CLICK, self.on_bubble)

        # Initialize state variables
        self.upd_error_count = 0
        self.checking_updates = False
        self.updates_available = False
        self.shutdown_scheduled = False
        self.reboot_scheduled = False
        self.bootup_time = get_boot_up_time()

        # Start update timer if interval and method are defined
        if update_interval and update_method:
            self.timer = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
            self.timer.Start(update_interval)
            if update_startup:
                # Optionally trigger an update after startup
                self.on_timer(None)

        # Check for logs and status on system startup
        if check_bootup_log:
            last_check = read_last_sync_time()
            now = datetime.datetime.now()

            # If system started within last hour AND last sync was within last 30 minutes
            if self.bootup_time is not None and last_check is not None:
                if (
                        (self.bootup_time + datetime.timedelta(hours=1) > now) and
                        (self.bootup_time + datetime.timedelta(minutes=30) > last_check)
                ):
                    log, error_log, reboot = check_eventlog(self.bootup_time)

                    if error_log is not None:
                        # Display balloon message indicating an error during startup
                        error_str = _("Update error detected during system start-up.")
                        self.ShowBalloon(title=_('WPKG Error'), text=error_str, msec=20 * 1000, flags=wx.ICON_ERROR)

                        # Show detailed error log in a dialog
                        title = _("System start error")
                        dlg = ViewLogDialog(title=title, log=error_log)
                        dlg.ShowModal()

        # Check if the last system upgrade was recent; if not, prompt user to upgrade
        if check_last_upgrade:
            last_sync = read_last_sync_time()
            if last_sync is not None:
                # If last sync was more than 'last_upgrade_interval' days ago
                if last_sync < (datetime.datetime.now() - datetime.timedelta(days=last_upgrade_interval)):
                    dlg_str = _("System should be updated!\n\n"
                                "System wasn't updated in over {} days.").format(str(last_upgrade_interval))
                    dlg = wx.MessageDialog(None, dlg_str, _("Attention!"), wx.OK | wx.ICON_EXCLAMATION)
                    dlg.ShowModal()

                    # Automatically trigger upgrade process
                    self.on_upgrade(None)

    def CreatePopupMenu(self):
        """
        Creates and returns the context menu for the system tray icon.
        Adds menu items based on current application state and configuration.
        """
        menu = wx.Menu()

        # Add "Check for updates" if update_method is defined
        if update_method:
            create_menu_item(menu, _("Check for updates"), "update", self.manual_timer)

        # Add "System update" option
        create_menu_item(menu, _("System update"), "upgrade", self.on_upgrade)

        # Separator between different sections
        menu.AppendSeparator()

        # Add "Help" option
        create_menu_item(menu, _("Help"), "help", self.on_about)

        # Optionally add "Contact IT Department" if button is active
        if is_it_department_website_button_active:
            create_menu_item(menu, _("Contact IT Department"), "help", self.open_it_department_website)

        # Add "Cancel shutdown" if a shutdown is scheduled
        if self.shutdown_scheduled:
            menu.AppendSeparator()
            create_menu_item(menu, _("Cancel shutdown"), "cancel", self.on_cancel_shutdown)

        # Add "Close" option if quitting is allowed
        if allow_quit:
            menu.AppendSeparator()
            create_menu_item(menu, _("Close"), "quit", self.on_exit)

        return menu

    def manual_timer(self, evt):
        """
        Triggered when the manual timer fires.
        This method sets the 'show_no_updates' flag to True and then
        delegates further handling to the on_timer method.

        Args:
            evt: The event object associated with the timer event.
        """
        # Indicate that 'no updates' should be shown on manual trigger
        self.show_no_updates = True
        # Delegate event handling to the on_timer method
        self.on_timer(evt)

    def on_timer(self, evt):
        """
        Called when the timer event is fired.
        Checks if an update process should be started, depending on the update method
        and whether a WPKG process is currently running.

        Args:
            evt: The event object associated with the timer.
        """
        # If using 'wpkg-gp' update method, check if WPKG is currently running
        if update_method == 'wpkg-gp':
            if is_wpkg_running():
                # Do not proceed with update if WPKG is already running
                return

        # Start the update check in a worker thread;
        # self.update_check_done is the callback, self.update_check does the actual work
        startWorker(self.update_check_done, self.update_check)

    def open_it_department_website(self, event):
        """
        Opens the default web browser and navigates to the website specified
        in the wpkg-gp_client.ini file.
        """
        # Open the specified URL in the default browser
        webbrowser.open(it_department_website)

    def update_check(self):
        """
        Checks for package updates depending on the specified update method.

        Returns:
            list or str: A list of updates if successful, or an error message if a problem occurred.
        """
        if update_method == 'wpkg-gp':
            # Using WPKG Group Policy update method
            updates = wpkggp_query(update_filter, update_blacklist)
        else:
            # Check if update_url is provided for remote package retrieval
            if update_url is None:
                return "Error: update_url must be provided for this update method."
            local_packages = get_local_packages(xml_file)
            remote_packages, error = get_remote_packages(update_url)
            if error:
                return str(error)
            # Compare local and remote packages, considering any blacklisted packages
            updates = version_compare(local_packages, remote_packages, update_blacklist)
        return updates

    def update_check_done(self, result):
        # Update check function ended
        r = result.get()
        self.checking_updates = False
        if isinstance(r, str):
            # Error returned
            self.updates_available = False
            if self.upd_error_count < 2 and not self.show_no_updates:
                # only display update errors on automatic check after the third error in a row
                self.upd_error_count += 1
            else:
                error_str = _("Could not load updates:") + "\n" + r
                self.ShowBalloon(title=_('Update Error'), text=error_str, msec=20*1000, flags=wx.ICON_ERROR)
                # reset update error counter
                self.upd_error_count = 0
        elif r:
            self.upd_error_count = 0
            action_dict = {'update': _('UPD:') + '\t',
                           'install': _('NEW:') + '\t',
                           'remove': _('REM:') + '\t',
                           'downgrade': _('DOW:') + '\t'}
            # Updates Found
            self.updates_available = True
            text = ''
            for action, name, version in r:
                text += action_dict[action] + name + ', v. ' + version + '\n'
            self.ShowBalloon(title=_("Update(s) available:"), text=text, msec=20*1000, flags=wx.ICON_INFORMATION)
        else:
            # No Updates Found
            self.upd_error_count = 0
            self.updates_available = False
            if self.show_no_updates:
                self.ShowBalloon(title=_("No Updates"), text=_("No Updates available for this Device."), msec=5*1000, flags=wx.ICON_INFORMATION)
                self.show_no_updates = False

    def on_bubble(self, event):
        """
        Handles the bubble notification click event.

        If updates are available, initiates the upgrade process by calling on_upgrade.

        Args:
            event: The event object associated with the bubble notification.
        """
        # If updates are available, proceed to upgrade
        if self.updates_available:
            self.on_upgrade(None)

    def on_upgrade(self, event):
        """
        Handler for the upgrade event. Checks for pending reboot, displays dialogs,
        and starts the WPKG dialog if eligible.
        """
        try:
            # If dialog already exists and is shown, just bring it to the front
            if self.wpkg_dialog.IsShown():
                self.wpkg_dialog.Raise()
                return
        except AttributeError:
            # Dialog is not yet created; continue to open it.
            pass

        try:
            # Try to read the reboot pending time from the registry
            reboot_pending = read_reboot_pending_time()
        except OSError:  # WindowsError is an alias for OSError on Python 3
            print("Could not read reboot pending time")
            dlg_msg = _('Registry Error\n\nNo access to necessary registry key.')
            dlg = wx.MessageDialog(None, dlg_msg, app_name, wx.OK | wx.ICON_ERROR)
            try:
                dlg.ShowModal()
            finally:
                dlg.Destroy()
            return

        if reboot_pending and reboot_pending > self.bootup_time:
            # A reboot is required before proceeding
            print("Reboot is required before the system can be updated again")
            dlg_msg = _("Reboot required!\n\n"
                        "A reboot is required before the system\n"
                        "can be updated again.\n"
                        "Reboot now?")
            dlg = wx.MessageDialog(None, dlg_msg, app_name,
                                   wx.YES_NO | wx.YES_DEFAULT | wx.ICON_EXCLAMATION)
            try:
                if dlg.ShowModal() == wx.ID_YES:
                    # Perform reboot with short delay and notification
                    shutdown(1, time=5, msg=_("System will reboot now!"))
            finally:
                dlg.Destroy()

        elif reboot_pending:
            # Registry value is set, but boot-up time is past; reset it
            set_reboot_pending_time(reset=True)

        # Stop timer before starting upgrade, if enabled
        if hasattr(self, "timer") and update_method and update_interval:
            self.timer.Stop()

        # Display the WPKG update dialog
        self.wpkg_dialog = RunWPKGDialog(parent=self, title=_('System Update'))
        self.wpkg_dialog.ShowModal()

        # Track scheduled actions for application menu updates
        if getattr(self.wpkg_dialog, "shutdown_scheduled", False):
            self.shutdown_scheduled = True
        if getattr(self.wpkg_dialog, "reboot_scheduled", False):
            self.shutdown_scheduled = True
            self.reboot_scheduled = True

        self.wpkg_dialog.Destroy()
        self.wpkg_dialog = None

        # Restart timer after upgrade, if enabled
        if hasattr(self, "timer") and update_method and update_interval:
            self.timer.Start()

    def on_about(self, evt):
        """
        Handles the About dialog event.

        Opens and displays the application's help file in a modal dialog window.

        Args:
            evt: The event object associated with the About/help request.
        """
        # Create and configure the help dialog
        helpdlg = HelpDialog(help_file, title=_('WPKG-GP Client - Help'))
        helpdlg.Center()  # Center the dialog on the screen

        # Display the help dialog modally
        helpdlg.ShowModal()

    def on_cancel_shutdown(self, event):
        """
        Handles the cancel shutdown event.

        If a reboot is currently scheduled, updates the registry to note the pending reboot time.
        Cancels any planned shutdown or reboot operation and resets relevant flags.

        Args:
            event: The event object associated with the user's cancel action.
        """
        if self.reboot_scheduled:
            # If a reboot was previously scheduled, record the pending reboot time in the registry
            set_reboot_pending_time()

        # Cancel any scheduled shutdown by invoking the shutdown function with action code 3
        shutdown(3)

        # Reset scheduling flags
        self.reboot_scheduled = False
        self.shutdown_scheduled = False

    def on_exit(self, event):
        """
        Handles the application exit event.

        If the WPKG dialog window is currently open and visible, brings it to the front
        instead of closing the application. If an exception occurs while checking the
        dialog state (e.g., the dialog does not exist), destroys the application.

        Args:
            event: The event object that triggered the exit request.
        """
        try:
            # Check if the WPKG dialog is currently shown
            if self.wpkg_dialog.IsShown():
                # Bring the dialog window to the front
                self.wpkg_dialog.Raise()
                return
        except AttributeError:
            # AttributeError likely means 'wpkg_dialog' does not exist or is None
            print("AttibuteError: wpkg_dialog likely doesn't exist or is None")
            self.Destroy()
        except Exception as e:
            # Catch-all for any unexpected exceptions, ensures clean shutdown
            print(f"Unexpected exception during exit: {e}")
            self.Destroy()

class RunWPKGDialog(wx.Dialog):
    def __init__(self, parent=None, title='Temp'):
        """Constructor"""
        wx.Dialog.__init__(self, None, title=title)
        self.parent = parent
        self.shouldAbort = False
        self.running = False
        self.wpkg_start_time = None
        self.shutdown_scheduled = False
        self.reboot_scheduled = False
        self.log = ""
        self.init_ui()
        size_y = self.GetEffectiveMinSize()[1]
        self.SetSize((410, size_y))

    def init_ui(self):
        """
           Initializes the user interface for the update dialog.

           Sets up all controls (labels, buttons, checkboxes, progress gauge, etc.),
           lays out the widgets using sizers, and binds event handlers for user interaction.
           """
        self.panel = wx.Panel(self, wx.ID_ANY)
        # Info Text
        infotext = _('Close all open Applications, it is possible that programs will be closed without a warning '
                     'and system could reboot without further confirmation.')

        infobox = wx.StaticBox(self.panel, -1, _('Attention'))
        infoboxbsizer = wx.StaticBoxSizer(infobox, wx.VERTICAL)
        info = wx.StaticText(self.panel, label=infotext)
        info.Wrap(380)
        infoboxbsizer.Add(info, 0)

        self.gauge = wx.Gauge(self.panel, size=(24, 26))
        self.update_label = wx.StaticText(self.panel, label=_('Current Progress:'))
        self.update_box = wx.TextCtrl(self.panel, style=wx.TE_READONLY)
        self.update_box.SetBackgroundColour(wx.WHITE)
        self.update_box.SetValue(_('Ready'))
        self.chk_shutdown = wx.CheckBox(self.panel, size=(160,20), label=_("Shutdown after update"))

        self.logButton = wx.Button(self.panel, size=(54,26), label="LOG")
        self.logButton.SetToolTip(wx.ToolTip(_('Open WPKG Log')))
        self.logButton.SetBitmap(img.get('log'))
        self.startButton = wx.Button(self.panel, label=_("Update"))
        self.abortButton = wx.Button(self.panel, label=_("Cancel"))
        self.logButton.Disable()
        self.abortButton.Disable()

        self.line = wx.StaticLine(self.panel, -1, size=(2,2), style=wx.LI_HORIZONTAL)
        self.startButton.Bind(wx.EVT_BUTTON, self.on_start_button)
        self.abortButton.Bind(wx.EVT_BUTTON, self.on_abort_button)
        self.logButton.Bind(wx.EVT_BUTTON, self.on_log_button)

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

    def on_start_button(self, event):
        if is_wpkg_running():
            dlg_msg = _("WPKG is currently running,\n"
                        "please wait a few seconds and try again.")
            dlg = wx.MessageDialog(self, dlg_msg, app_name, wx.OK | wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return
        dlg_title = _("2. Warning")
        dlg_msg = _("Close all open programs!\n\nThe System could restart without further confirmation!\n\n" \
                    "Continue?")
        dlg = wx.MessageDialog(self, dlg_msg, dlg_title, wx.YES_NO|wx.YES_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            dlg.Destroy()
            # Disable/enable buttons and disable Close Window option!
            self.startButton.Disable()
            self.abortButton.Enable()
            self.EnableCloseButton(enable=False)
            # Set Start Time
            self.wpkg_start_time = datetime.datetime.now()
            # Reset Log
            self.log = None
            startWorker(self.LongTaskDone, self.LongTask)

    def on_abort_button(self, e):
        if not self.running:
            self.Close()
            return
        dlg_title = _("Cancel")
        dlg_msg = _("System update in progress!\n\n Canceling this Progress could result in installation issues.\n"
                    "Cancel?")
        dlg = wx.MessageDialog(self, dlg_msg, dlg_title, wx.YES_NO|wx.YES_DEFAULT|wx.ICON_EXCLAMATION)
        if dlg.ShowModal() == wx.ID_YES:
            dlg.Destroy()
            if not self.running:
                # WPKG Process by this client has finished, no cancel possible
                return
            print('Aborting WPKG Process') #TODO: MOVE TO DEBUG LOGGER
            self.shouldAbort = True
            msg = 'Cancel'
            try:
                pipeHandle = CreateFile("\\\\.\\pipe\\WPKG", GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
            except pywintypes.error as xxx_todo_changeme:
                (n, f, e) = xxx_todo_changeme.args
                print("Error when generating pipe handle: %s" % e) #TODO: MOVE TO DEBUG LOGGER
                return 1

            SetNamedPipeHandleState(pipeHandle, PIPE_READMODE_MESSAGE, None, None)
            WriteFile(pipeHandle, msg)

    def LongTask(self):
        return_msg = None
        return_code = None
        reboot = False
        # Checking if System is connected through VPN
        if check_vpn:
            if is_cisco_secure_client_vpn_connected(arch=arch):
                self.update_box.SetValue(_('Looking for an active VPN-Connection.'))
                dlg_msg = _("WPKG-GP Client detected a active VPN Connection using Cisco Anyconnect.\n"
                        "This could result in slow upgrade progress and updates for the AnyConnect\n"
                        "Software will be blocked.\n"
                        "Continue?")
                dlg = wx.MessageDialog(self, dlg_msg, app_name, wx.YES_NO | wx.YES_DEFAULT | wx.ICON_INFORMATION)
                if dlg.ShowModal() == wx.ID_NO:
                    # Canceled by user because of active VPN Connection
                    return_msg = _("WPKG process start cancelled by user.")
                    return 400, return_msg, None
        # LONG TASK is the PipeConnection to the WPKG-GP Windows Service
        self.running = True
        msg = 'ExecuteNoReboot'
        try:
            pipeHandle = CreateFile("\\\\.\\pipe\\WPKG", GENERIC_READ|GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
        except pywintypes.error as xxx_todo_changeme1:
            # print "Error when generating pipe handle: %s" % e
            # Can't connect to pipe error, probably service not running
            (n, f, e) = xxx_todo_changeme1.args
            print ("Error when generating pipe handle: %s" % e)
            # Can't connect to pipe error, probably service not running
            return_msg = _("Error: WPKG-GP Service not running.")
            return 208, return_msg, None

        SetNamedPipeHandleState(pipeHandle, PIPE_READMODE_MESSAGE, None, None)
        WriteFile(pipeHandle, msg.encode('utf-8'))
        while 1:
            try:
                (hr, readmsg) = ReadFile(pipeHandle, 512)
                out = readmsg[4:].decode('utf-8')  #Strip 3 digit status code, decode characters
                status_code = int(readmsg[:3])
                if status_code < 102:
                    # default status code for pipe updates
                    percentage = get_percentage(out)
                    wx.CallAfter(self.update_box.SetValue, out)
                    wx.CallAfter(self.gauge.SetValue, percentage)
                elif status_code > 300:
                    # reboot necessary
                    reboot = True
                elif status_code > 200:
                    # possible error
                    return_code = status_code
                    return_msg = out
            except win32api.error as exc:
                if exc.winerror == winerror.ERROR_PIPE_BUSY:
                    win32api.Sleep(5000)
                    print('Pipe Busy Error')
                    continue
                break

        return return_code, return_msg, reboot

    def LongTaskDone(self, result):
        self.running = False
        self.chk_shutdown.Disable()
        chk_shutdown = self.chk_shutdown.IsChecked()
        self.gauge.SetValue(100)
        return_code, return_msg, reboot = result.get()
        # Get WPKG Log
        self.log, error_log = check_eventlog(self.wpkg_start_time)
        if self.shouldAbort:
            self.update_box.SetValue(_('WPKG-GP process aborted.'))
            if return_code == 200:
                # display the error msg ?
                print(return_msg)
        elif return_code == 400 or return_code == 105:
            self.update_box.SetValue(return_msg)
        elif return_code and return_code != 200:
            self.update_box.SetValue(return_msg)
            dlg_title = _("WPKG-GP Notification")
            dlg_icon = wx.ICON_INFORMATION
            if return_code == 201:
                dlg_msg = _("WPKG-GP is currently running a task.\n"
                            "Retry later.")
            elif return_code == 204:
                dlg_msg = _("The update server could not be reached.")
                dlg_icon = wx.ICON_ERROR
            elif return_code == 205:
                dlg_msg = _("The system was rejected from the server to execute an update!\n"
                            "Contact your IT department for further information.")
            elif return_code == 207:
                dlg_msg = _("You are not authorized to execute a wpkg update!\n"
                            "Contact your IT department for further information.")
            elif return_code == 208:
                dlg_msg = _("Can't connect to the wpkg-gp service.")
                dlg_icon = wx.ICON_ERROR
            else:
                dlg_msg = _('Unknown problem occurred.') + '\n Status code: ' + str(return_code) + '\n' + return_msg
            dlg = wx.MessageDialog(self, dlg_msg, dlg_title, wx.OK | dlg_icon)
            dlg.ShowModal()
        else:
            if reboot:
                self.update_box.SetValue(_('WPKG-GP process finished, restart necessary!'))
            else:
                self.update_box.SetValue(_('WPKG-GP process finished.'))
        if error_log:
            log_dlg = ViewLogDialog(title=_("Error detected during update"), log=error_log)
            log_dlg.ShowModal()
            log_dlg.Destroy()
        if reboot and not chk_shutdown and not self.shouldAbort:
            # reboot pending, no abort and no shutdown configured
            dlg_msg = _("Reboot required!\n\n"
                        "For the completion of the installation(s), a reboot is required.\n"
                        "Reboot now?")
            dlg = wx.MessageDialog(self, dlg_msg, app_name, wx.YES_NO | wx.YES_DEFAULT | wx.ICON_EXCLAMATION)
            if dlg.ShowModal() == wx.ID_YES:
                # Initiate reboot
                shutdown(1, time=shutdown_timeout, msg=_('System will reboot in %TIME% seconds.'))
                self.reboot_scheduled = True
                self.Close()
            else:
                # Reboot is pending
                set_reboot_pending_time()
        elif chk_shutdown and not self.shouldAbort and not return_code:
            # shutdown configured, wpkg process not canceled and no error occurred
            shutdown(2, time=shutdown_timeout, msg=_('System will shutdown in %TIME% seconds.'))
            if reboot:
                self.reboot_scheduled = True
            else:
                self.shutdown_scheduled = True
            self.Close()
        if not self.log:
            self.log.append(_("No System changes."))
        self.logButton.Enable()
        self.abortButton.SetLabel(_('Close'))
        self.shouldAbort = False
        self.EnableCloseButton(enable=True)

    def on_log_button(self, evt):
        """
        Handles the event when the log button is clicked.

        Opens a modal dialog to display the WPKG log with a timestamp in the window title.

        Args:
            evt: The event object associated with the button click.
        """
        # Format the title with the WPKG start time for user context
        title = 'WPKG Log - {}'.format(self.wpkg_start_time.strftime("%Y/%m/%d %H:%M:%S"))

        # Create the log viewing dialog, passing the title and log content
        logdlg = ViewLogDialog(title=title, log=self.log)

        # Show the dialog modally (blocks until closed)
        logdlg.ShowModal()


class ViewLogDialog(wx.Dialog):
    def __init__(self, title='Temp', log="Temp"):
        """Constructor"""
        wx.Dialog.__init__(self, None, title=title, style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.log = "\n".join(log)
        self.init_ui()
        self.SetSize((640, 480))

    def init_ui(self):
        """
        Initializes the user interface for the log display window.

        Sets up a panel containing a read-only, multi-line text box to display the log,
        arranges controls using a vertical box sizer, and centers the window on the screen.
        Also binds the window close event to the on_close handler.
        """
        # Create the main panel for the window
        self.panel = wx.Panel(self, wx.ID_ANY)

        # Create a read-only, multi-line text box for displaying the log
        self.textbox = wx.TextCtrl(
            self.panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        self.textbox.SetValue(self.log)

        # Set up the layout using a vertical box sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.textbox, 1, wx.ALL | wx.EXPAND, 5)

        # Apply the sizer to the panel and adjust window size
        self.panel.SetSizerAndFit(sizer)

        # Center the window on the screen
        self.Center()

        # Bind the close event to the on_close handler
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_close(self, evt):
        """
        Handles the close event for the window.

        Destroys the window and releases all associated resources.
        """
        # Destroy the window and clean up resources
        self.Destroy()


if __name__ == '__main__':
    app = wx.App(False)
    # Translation configuration
    mylocale = wx.Locale(wx.LANGUAGE_DEFAULT)
    # TODO: Add config option or settings to force language? e.g.: wx.Locale(language=wx.LANGUAGE_FRENCH)
    localedir = os.path.join(bundle_path, "locale")
    mylocale.AddCatalogLookupPathPrefix(localedir)
    mylocale.AddCatalog('wpkg-gp-client')

    # If config file could not be opened
    if no_config:
        dlgmsg = _('Can\'t open config file "{}"!').format("wpkg-gp_client.ini")
        dlg = wx.MessageDialog(None, dlgmsg, app_name, wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        sys.exit(1)

    # If an instance of WPKG-GP Client is running already in the users session
    if is_multiple_client_instances_in_session():
        dlgmsg = _("An instance of WPKG-GP Client is already running!")
        dlg = wx.MessageDialog(None, dlgmsg, app_name, wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        sys.exit()

    # If the required WPKG-GP Service is installed
    if not check_wpkggp_version(req_wpkggp_ver):
        dlgmsg = _("WPKG-GP Client requires at least version"
                   " {} of the WPKG-GP Service.").format(req_wpkggp_ver)
        dlg = wx.MessageDialog(None, dlgmsg, app_name, wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        sys.exit()

    # Set help file
    if not help_file or help_file.lower() == "default":
        help_file = get_help_translation_file(client_path, mylocale.Name)
    else:
        # Construct the full path to the custom help file
        help_file = os.path.join(client_path, help_file)

    TRAY_ICON = os.path.join(bundle_path, 'img', 'apacheconf-16.png')
    TaskBarIcon(trayicon=TRAY_ICON, tooltip=app_name)
    app.MainLoop()

