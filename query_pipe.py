# -*- encoding: utf-8 -*-
from win32pipe import *
from win32file import *
import pywintypes
import win32api
import winerror
import sys
import subprocess
import re
import datetime
import os
import locale
import win32con
import _winreg

def get_codepage():
    try:
        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, R"SYSTEM\CurrentControlSet\Control\Nls\CodePage", 0, _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY)
        codepage = _winreg.QueryValueEx(key, "OEMCP")[0]
        _winreg.CloseKey(key)
    except WindowsError:
        print 'Registy Error: Can\'t read codepage'
        codepage = '1252'
    return 'cp' + codepage

def wpkggp_query(cp):
    msg = 'Query'
    error_msg = None
    packages = []
    try:
        pipeHandle = CreateFile("\\\\.\\pipe\\WPKG", GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
    except pywintypes.error, (n, f, e):
        # print "Error when generating pipe handle: %s" % e
        error_msg = u"Error: WPKG-GP Service not running"
        return error_msg

    SetNamedPipeHandleState(pipeHandle, PIPE_READMODE_MESSAGE, None, None)
    WriteFile(pipeHandle, msg)
    n = 0
    while 1:
        try:
            (hr, readmsg) = ReadFile(pipeHandle, 512)
            out = readmsg[4:]  # Strip 3 digit status code
            # print repr(out) # DEBUG!
            n += 1
            if n > 1:
                #packages.append(out.decode('utf-8').split('\t'))
                out = out.decode(cp)
                for n in ['TASK: ', 'NAME: ', 'REVISION: ']:
                    out = out.replace(n, '')
                packages.append(out.split('\t'))
            if out.startswith('Error') or out.startswith('Info'):
                error_msg = out

        except win32api.error as exc:
            if exc.winerror == winerror.ERROR_PIPE_BUSY:
                win32api.Sleep(5000)
                print 'Pipe Busy Error'
                continue
            break

    return packages, error_msg


cp = get_codepage()
print cp

packages, error = wpkggp_query(cp)
if not error:
    print repr(packages)
else:
    print error
# Check if the query commands modifies the file date of wpkg.xml !
wpkgfile = "C:\Windows\Sysnative\wpkg.xml"
time = datetime.datetime.fromtimestamp(os.path.getmtime(wpkgfile))
print time
