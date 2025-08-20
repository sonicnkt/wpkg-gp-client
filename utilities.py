# -*- encoding: utf-8 -*-
import platform
import psutil
import subprocess
import xml.etree.cElementTree as ET

from packaging.version import parse as parse_version
from urllib.request import urlopen
from urllib.error import URLError
import win32evtlog
import win32evtlogutil
import win32con
import winerror
import winreg
# Imports WPKGCOnnection:
from win32pipe import *
from win32file import *
import pywintypes
import win32api
import re
import traceback
import datetime
import os
import sys
import wx


msi_exit_dic = {"1619": "ERROR_INSTALL_PACKAGE_OPEN_FAILED",
                "1612": "ERROR_INSTALL_SOURCE_ABSENT"}

# set translation function
_ = wx.GetTranslation

def get_paths():
    """
    Returns the absolute path to the executable as well as the bundle (pyinstaller) directory "_internal".
    Uses sys.argv[0] as the entry point.
    """
    executable_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    bundle_path = os.path.abspath(os.path.dirname(__file__))
    return executable_path, bundle_path


def is_wpkg_running():
    """
    Checks if WPKG is running by reading the 'running' registry value.
    Returns True if 'running' is 'true', otherwise False.
    """
    try:
        # Open the registry key with read access (64-bit view)
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WPKG",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        ) as key:
            # Retrieve the value for 'running'
            running = winreg.QueryValueEx(key, "running")[0]
            # Return True if value is exactly the string 'true' (case-insensitive)
            return str(running).lower() == 'true'

    except FileNotFoundError:
        # Registry key or value does not exist
        print("'SOFTWARE\\WPKG' registry key or 'running' value not found.")
        return False
    except OSError as e:
        print(f"Failed to read 'running' value from 'SOFTWARE\\WPKG' in registry: {e}")
        return False


def check_wpkggp_version(required_version):
    """
    Check if the installed Wpkg-GP version is greater than or equal to the required version.

    Args:
        required_version (str): The version string to check against.

    Returns:
        bool: True if installed version >= required_version, False otherwise.
    """
    try:
        # Open registry key for Wpkg-Gp (64-bit view)
        with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Wpkg-Gp",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        ) as key:
            # Retrieve 'DisplayVersion' from registry
            installed_version = winreg.QueryValueEx(key, "DisplayVersion")[0]

            # Compare the installed version with the required version
            return parse_version(installed_version) >= parse_version(required_version)

    except FileNotFoundError:
        print("'SOFTWARE\\Wpkg-Gp' registry key or 'DisplayVersion' not found.")
        return False
    except OSError:
        print("Failed to read 'DisplayVersion' from 'SOFTWARE\\Wpkg-Gp' in registry.")
        return False


def check_system_architecture():
    """
    Detects system architecture and constructs the correct path to wpkg.xml.

    Returns:
        tuple: (full_path_to_wpkg.xml, architecture_string)
        architecture_string is either "x86" or "x64"
    """
    # Determine the architecture
    machine = platform.machine()
    if machine.endswith('64'):
        # This means a 64-bit process on 64-bit Windows
        sys_folder = "System32"
        architecture = "x64"
    else:
        # Use 'Sysnative' to access the real System32 folder
        sys_folder = "Sysnative"
        architecture = "x86"

    # Construct full path to wpkg.xml in the appropriate system folder
    system_root = os.getenv('SystemRoot', 'C:\\Windows')
    xml_file = os.path.join(system_root, sys_folder, "wpkg.xml")
    return xml_file, architecture


def get_help_translation_file(path, language):
    """
    Returns the relative path to the appropriate help file for the specified language.
    Falls back to English help file if the translation does not exist.

    Args:
        path (str): The base directory where the 'help' folder is located.
        language (str): Language code, e.g., 'de_DE' or 'fr'.

    Returns:
        str: Relative path to the language-specific help file or the default English help file.
    """
    # Get the first two characters of the language string (ISO 639-1 code)
    help_lang = language[:2].lower()
    help_folder_path = os.path.join(path, 'help')

    # Build the path for the translated help file
    help_file_path = os.path.join(help_folder_path, f'help_{help_lang}.md')

    # If help file for the language exists, return its relative path.
    if os.path.isfile(help_file_path):
        return os.path.relpath(help_file_path, path)
    else:
        # Fallback: return the English help file relative path, using os.path.join for platform compatibility
        print(f"'help_{help_lang}.md' file not found. Returning Fallback.")
        return os.path.join('help', 'help_en.md')


def is_multiple_client_instances_in_session():
    """
    Checks if more than one instance of 'WPKG-GP-Client.exe' is running in the current Windows session.
    Returns:
        bool: True if multiple client instances found in current session, else False.
    """
    client_instance_count_in_session = 0
    client_task_list = []
    session_id = None

    try:
        # Run 'tasklist' and capture the output, ensure output is decoded as text
        output = subprocess.check_output(
            ["tasklist"], creationflags=0x08000000
        ).decode('utf-8', errors='ignore')

        # Split into lines and remove the first 3-4 header lines
        lines = output.strip().split('\n')
        # Remove header lines. Number of header lines may vary depending on Windows version/language
        # We'll skip any line until we find the header that contains 'Image Name'
        data_started = False
        prog = []
        for line in lines:
            if "Image Name" in line and "PID" in line:
                data_started = True
                continue
            if not data_started:
                continue
            # Split line into entries (some columns may merge if the process name or user has spaces)
            parts = line.split()
            if parts:
                prog.append(parts)

        for entry in prog:
            # Check for client process, check for sufficient columns before accessing
            if entry[0] == 'WPKG-GP-Client.exe':
                # Assume: [Image Name, PID, Session Name, Session#, Mem Usage]
                if len(entry) >= 4:
                    client_task_list.append((entry[0], entry[3])) # (process, session id)
            # Find sessionid of the current 'tasklist.exe' process
            elif entry[0] == 'tasklist.exe':
                if len(entry) >= 4:
                    session_id = entry[3]

        # Count client instances in this session
        if session_id:
            client_instance_count_in_session = sum(1 for process, s_id in client_task_list if s_id == session_id)

        return client_instance_count_in_session > 1

    except Exception as e:
        print(f'Error while checking client process: {e}')
        return False


def shutdown(mode, time=60, msg=None):
    """
    Executes a Windows system shutdown, restart, or cancel command.

    Args:
        mode (int): 1 for reboot, 2 for shutdown, 3 for abort/cancel shutdown.
        time (int): Wait time before shutdown or restart, in seconds.
        msg (str, optional): Message to display with the shutdown notification. Supports '%TIME%' placeholder.

    Returns:
        None
    """
    shutdown_base_cmd = ["shutdown.exe"]

    if mode == 1:
        # Reboot system
        shutdown_cmd = shutdown_base_cmd + ["/f", "/r", "/t", str(time)]
    elif mode == 2:
        # Shutdown system
        shutdown_cmd = shutdown_base_cmd + ["/f", "/s", "/t", str(time)]
    elif mode == 3:
        # Abort scheduled shutdown
        shutdown_cmd = shutdown_base_cmd + ["/a"]
    else:
        print("mode needs to be 1 (reboot), 2 (shutdown), or 3 (cancel/abort).")
        return

    # Only add comment message if not aborting/cancelling shutdown
    if mode in (1, 2) and msg:
        # If the message contains "%TIME%", replace it with the actual time
        shutdown_message = msg.replace("%TIME%", str(time)) if "%TIME%" in msg else msg
        shutdown_cmd += ["/c", shutdown_message]

    # Launch the command with no console window
    create_no_window = 0x08000000
    try:
        subprocess.call(
            shutdown_cmd,
            creationflags=create_no_window,
            shell=False  # Do not use shell
        )
    except Exception as e:
        print(f"Error executing shutdown command: {e}")


def set_reboot_pending_time(reset=False):
    """
        Sets or resets the 'RebootPending' timestamp in the Windows registry under
        'SOFTWARE\\Wpkg-GP-Client'. If reset=True, the value is cleared ('None').
        If reset=False, the value is set to the current date and time.

        Args:
            reset (bool): If True, resets (clears) the reboot pending timestamp.
                          If False, sets it to current datetime.
        """
    # Determine value to store
    if reset:
        value = "None"
    else:
        # Format: 'YYYY-MM-DD HH:MM:SS'
        value = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Open or create the specified registry key with write access
        with winreg.CreateKeyEx(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Wpkg-GP-Client",
                0,
                winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_64KEY
        ) as key:
            # Set or reset the 'RebootPending' value
            winreg.SetValueEx(key, "RebootPending", 0, winreg.REG_EXPAND_SZ, value)
    except OSError as e:
        print(f"Failed to set 'RebootPending' in registry: {e}")


def read_reboot_pending_time():
    """
       Reads the 'RebootPending' value from the registry and parses it as a datetime object.
       Returns:
           datetime.datetime object if a valid timestamp is stored, otherwise None.
       """
    try:
        # Open or create the registry key
        with winreg.CreateKeyEx(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Wpkg-GP-Client",
                0,
                winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_64KEY
        ) as key:
            try:
                reboot_pending_value = winreg.QueryValueEx(key, "RebootPending")[0]
            except FileNotFoundError:
                # 'RebootPending' value does not exist
                print(f"Failed to read 'RebootPending' in registry: {key}")
                return None

        # Try to parse the value as datetime (will fail if value is "None" or not a valid date string)
        try:
            reboot_pending_time = datetime.datetime.strptime(reboot_pending_value, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            print(f"Failed to parse 'RebootPending' in registry: {key}")
            return None

        return reboot_pending_time

    except OSError as e:
        # Could not access the registry key
        print(f"Failed to read 'RebootPending' from registry: {e}")
        return None


def read_last_sync_time():
    """
    Reads the 'lastsync' value from the registry and parses it as a datetime object.

    Returns:
        datetime.datetime: The parsed last sync time, or None if not available or invalid.
    """
    try:
        with winreg.CreateKeyEx(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WPKG",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        ) as key:
            try:
                last_sync_value = winreg.QueryValueEx(key, "lastsync")[0]
            except FileNotFoundError:
                print("'lastsync' not found in registry.")
                return None

        try:
            last_sync_time = datetime.datetime.strptime(last_sync_value, '%Y-%m-%d %H:%M:%S')
            return last_sync_time
        except (ValueError, TypeError) as e:
            print(f"Failed to parse 'lastsync': {e}")
            return None

    except FileNotFoundError:
        print("Registry key 'SOFTWARE\\WPKG' not found!")
        return None
    except PermissionError:
        print("Not enough permissions to read Registry Key 'SOFTWARE\\WPKG'! Run as Administrator.")
        return None
    except OSError as e:
        print(f"Failed to read 'lastsync' from registry: {e}")
        return None


def is_cisco_secure_client_vpn_connected(arch="x64"):
    """
    Checks if Cisco Secure Client VPN is currently connected.

    Args:
        arch (str): 'x64' for 64-bit or 'x86' for 32-bit (determines path to VPN client).

    Returns:
        bool: True if VPN is connected, False otherwise.
    """
    # Construct the path to the vpncli.exe based on system architecture
    
    if arch == "x64": program_files = "%PROGRAMFILES(X86)%"
    else: program_files = "%PROGRAMFILES%"
    vpn_path = os.path.join(program_files, "Cisco", "Cisco Secure Client", "vpncli.exe")
    vpn_path = os.path.expandvars(vpn_path)

    # Run the vpncli.exe command to check VPN status
    try:
        # Run vpncli.exe status and capture output
        result = subprocess.run(
            [vpn_path, "status"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        connected_strings = ["state: connected", "status: verbunden", "estado: conectado"]
        output_lower = result.stdout.lower()
        if any(connected_str in output_lower for connected_str in connected_strings):
            return True
        else:
            return False

    except Exception as e:
        print(f"Error checking VPN status: {e}")
        return False


def get_percentage(text):
    """
    Extracts a progress percentage from a string in the form '(current/max)'.

    Args:
        text (str): The string containing the progress in the format '(x/y)'.

    Returns:
        int: The progress as an integer percentage (0-99).
    """
    pattern = re.compile(r'\((\d{1,3})/(\d{1,3})\)')
    try:
        # Try to find the pattern and extract the groups
        match = pattern.search(text)
        if not match:
            # Pattern not found, assume 1% as fail-safe
            print(f"Failed to extract progress from '{text}'")
            return 1

        current, maximum = match.groups()
        current = float(current)
        maximum = float(maximum)
        # Avoid division by zero
        if maximum == 0:
            print(f"Division by zero detected in '{text}'")
            return 1

        progress = (current / maximum) * 100
    except Exception as e:
        # Catch any unexpected errors and default to 1%
        print(f"Error in get_percentage: {e}")
        return 1

    # If exactly 100%, return 99 instead (as per original logic)
    if int(progress) == 100:
        return 99
    else:
        return int(progress)


def get_boot_up_time():
    """
    Retrieves the last system boot-up time using WMIC and returns it as a datetime object.

    Returns:
        datetime.datetime: The system boot-up time, or None if it cannot be determined.
    """
    try:
        boot_time_timestamp = psutil.boot_time()
        boot_time = datetime.datetime.fromtimestamp(boot_time_timestamp)
        return boot_time
    except Exception as e:
        print(f"Failed to retrieve boot-up time: {e}")
        return None


def wpkggp_query(task_filter, blacklist_prefix):
    """
    Queries the WPKG-GP service using a named pipe and retrieves package tasks,
    filtering and sorting the results.

    Args:
        task_filter (list of str): Task names to include (e.g. ["install", "update"]).
        blacklist_prefix (str): String; package names starting with this prefix (case-insensitive) will be excluded.

    Returns:
        list: A sorted list of valid package entries, or an error message string if a problem occurred.
    """
    msg = 'Query'
    error_msg = None
    packages = []

    try:
        # Attempt to open the named pipe
        pipe_handle = CreateFile(
            r"\\.\pipe\WPKG",
            GENERIC_READ | GENERIC_WRITE,
            0, None, OPEN_EXISTING, 0, None
        )
    except pywintypes.error as e:
        # Most likely, the service is not running
        print(f"Failed to create pipe: {e}")
        error_msg = "Error: WPKG-GP Service not running"
        return error_msg

    # Set the named pipe to message mode
    SetNamedPipeHandleState(pipe_handle, PIPE_READMODE_MESSAGE, None, None)
    WriteFile(pipe_handle, msg.encode('utf-8'))

    while True:
        try:
            hr, readmsg = ReadFile(pipe_handle, 512)
            # Make sure we decode bytes to string only if necessary
            if isinstance(readmsg, bytes):
                status_code = int(readmsg[:3].decode('utf-8'))
                out = readmsg[4:].decode('utf-8')
            else:
                status_code = int(readmsg[:3])
                out = readmsg[4:]

            if status_code == 103:
                # DEBUG
                repr(out)
                # Query output: remove tags and split by tabs
                for tag in ['TASK: ', 'NAME: ', 'REVISION: ']:
                    out = out.replace(tag, '')
                package = out.split('\t')

                # Filtering by task and blacklist prefix
                if len(package) >= 2 and package[0] in task_filter:
                    if not package[1].lower().startswith(blacklist_prefix):
                        packages.append(package)

            elif status_code == 104:
                # No pending updates; skip
                continue
            elif status_code > 200:
                # Received error from service
                if status_code == 203:
                    error_msg = "Error: Query function not supported in the installed wpkg-gp version."
                else:
                    error_msg = out
        except win32api.error as exc:
            if hasattr(exc, "winerror") and exc.winerror == winerror.ERROR_PIPE_BUSY:
                win32api.Sleep(5000)
                print("Pipe Busy Error")
                continue  # Retry after waiting
            break  # Any other error, exit loop

    # Return error message or sorted package list
    if error_msg:
        return error_msg
    else:
        # Sort the packages based on predefined task order
        sort_order = {"install": 0, "update": 1, "downgrade": 2, "remove": 3}
        packages.sort(key=lambda val: sort_order.get(val[0], 99))
        return packages


def resolve_variable(child, pkg_version):
    """
    Resolves a variable like %VAR% in a package revision string by looking it up in child element variables.

    Args:
        child (xml.etree.ElementTree.Element): The package XML element.
        pkg_version (str): The revision/value string possibly containing a %VARIABLE%.

    Returns:
        tuple: (variable, value) where variable is the matched %VAR% and value is the replacement string.
    """
    match = re.search(r'(%[^%]+%)', pkg_version)
    if not match:
        return '', pkg_version
    variable = match.group(1)
    variable_name = variable.strip('%')
    value = None
    try:
        for entry in child.iterfind('variable[@name="{}"]'.format(variable_name)):
            value = entry.attrib.get('value')
            break  # Use only the first match
        if value is None:
            value = ''
        return variable, value
    except Exception:
        print(f"Failed to resolve variable {variable_name}")
        return variable, ''


def get_local_packages(xml_path):
    """
    Parses the XML file and resolves variables in package revisions.

    Args:
        xml_path (str): The path to the XML file.

    Returns:
        dict: Mapping of package id to [name, resolved_revision]
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    local_packages = {}
    for child in root.iter('package'):
        pkg_id = child.attrib.get('id', '')
        pkg_name = child.attrib.get('name', '')
        pkg_version = child.attrib.get('revision', '')
        # Resolve variables if present in the revision string (supports nested variables once)
        if '%' in pkg_version:
            variable, value = resolve_variable(child, pkg_version)
            # Deal with nested variable (one level only)
            if variable and '%' in value:
                variable2, value2 = resolve_variable(child, value)
                value = value.replace(variable2, value2)
            pkg_version = pkg_version.replace(variable, value)
        local_packages[pkg_id] = [pkg_name, pkg_version]
    return local_packages


def get_remote_packages(url):
    """
    Fetches and parses the remote XML package list.

    Args:
        url (str): The remote URL to fetch the XML from.

    Returns:
        tuple: (remote_packages, error_message)
               remote_packages is a dict {package_id: version}
               error_message is None if no error occurred, else the error as a string.
    """
    error_message = None
    remote_packages = {}

    try:
        # Download the XML data with a timeout
        response = urlopen(url, timeout=5)
        xml_data = response.read()
    except (IOError, URLError) as e:
        # Return empty dict and error if fetching fails
        print(f"Failed to fetch remote package list: {e}")
        return {}, str(e)

    try:
        # Parse the XML and extract package info
        root = ET.fromstring(xml_data)
        for child in root.iter('package'):
            pkg_id = child.attrib.get('id')
            pkg_version = child.attrib.get('version')
            if pkg_id and pkg_version:
                remote_packages[pkg_id] = pkg_version
    except ET.ParseError as e:
        # Return empty dict if parsing fails
        print(f"Failed to parse remote package list: {e}")
        return {}, f"XML Parse Error: {e}"

    return remote_packages, error_message


def version_compare(local, remote, blacklist):
    """
    Compares local and remote package versions and collects packages that need updating.

    Args:
        local (dict): Mapping of package id to [package_name, local_version]
        remote (dict): Mapping of package id to remote_version (str)
        blacklist (str): Lower-case prefix; if a package name starts with this, it is skipped

    Returns:
        list: Tuples of ('update', package_name, remote_version) for packages needing update
    """
    update_list = []
    for package_id, (package_name, local_version) in local.items():
        try:
            remote_version = remote[package_id]
            # Compare local and remote versions using version parsing
            if parse_version(local_version) < parse_version(remote_version):
                if not package_name.lower().startswith(blacklist):
                    update_list.append(('update', package_name, remote_version))
        except (KeyError, IndexError) as e:
            # Skip if package_id not in remote or badly formatted values
            print(f"Failed to get package version for {package_id}: {e}")
            continue
    return update_list


def check_eventlog(start_time, msi_exit_dic=None):
    """
    Fetches events from the Windows Application event log since start_time.
    Filters for WSH entries and collects errors/warnings.

    Args:
        start_time (datetime.datetime): Only events newer than this will be processed.
        msi_exit_dic (dict, optional): For mapping MSI exit codes to strings.

    Returns:
        tuple: (log_list, error_log_list)
    """
    # Define event type mapping
    evt_dict = {
        win32con.EVENTLOG_AUDIT_FAILURE: 'AUDIT_FAILURE',
        win32con.EVENTLOG_AUDIT_SUCCESS: 'AUDIT_SUCCESS',
        win32con.EVENTLOG_INFORMATION_TYPE: 'INFORMATION',
        win32con.EVENTLOG_WARNING_TYPE: 'WARNING',
        win32con.EVENTLOG_ERROR_TYPE: 'ERROR',
        0: 'INFORMATION'
    }

    computer = 'localhost'
    logtype = 'Application'
    log = []
    error_log = []

    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

    try:
        hand = win32evtlog.OpenEventLog(computer, logtype)
        events = True
        while events:
            try:
                events = win32evtlog.ReadEventLog(hand, flags, 0)
            except pywintypes.error as e:
                print(f"Failed to read the Event Logs: {e}", file=sys.stderr)
                break

            if not events:
                break

            for ev_obj in events:
                the_time = ev_obj.TimeGenerated.Format()  # Locale-dependent format
                try:
                    time_obj = datetime.datetime.strptime(the_time, '%c')
                except ValueError:
                    print(f"Failed to parse event time: {the_time}")
                    continue

                if time_obj < start_time:
                    # Too old, stop processing further (log is read backwards)
                    win32evtlog.CloseEventLog(hand)
                    return log, error_log

                computer_name = str(ev_obj.ComputerName)
                src = str(ev_obj.SourceName)
                evt_type = evt_dict.get(ev_obj.EventType, 'INFORMATION')
                try:
                    msg = str(win32evtlogutil.SafeFormatMessage(ev_obj, logtype))
                except (pywintypes.error, win32evtlog.error, Exception) as e:
                    print(f"Failed to format event messages: {e}", file=sys.stderr)
                    msg = "<Unable to format message>"

                # Only process WSH (WPKG-related) entries
                if src == 'WSH':
                    if not msg.startswith('User notification suppressed.'):
                        entry = " : ".join([the_time, computer_name, src, evt_type, '\n' + msg])
                        log.append(entry)
                    # Add warnings/errors to error_log
                    if evt_type in ("ERROR", "WARNING"):
                        if "msiexec" in msg and msi_exit_dic is not None:
                            try:
                                match = re.search(r"\((\d+)\)", msg)
                                if match:
                                    exit_code = match.group(1)
                                    msi_info = msi_exit_dic.get(exit_code, "Unknown MSI exit code")
                                    msg += f"\nMSI error ({exit_code}): {msi_info}"
                            except (AttributeError, IndexError, Exception) as e:
                                print(f'Could not determine MSI exit code: {e}', file=sys.stderr)

                        error_entry = " : ".join([the_time, computer_name, src, evt_type, '\n' + msg])
                        error_log.append(error_entry)
        win32evtlog.CloseEventLog(hand)
    except (pywintypes.error, OSError) as e:
        print(f"Failed to access the Event Log: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    return log, error_log