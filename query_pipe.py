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

def getActCP():
    p = subprocess.Popen('chcp', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    raw_out = out.encode('string_escape')
    cp = re.search('page: ([0-9]{1,4})', raw_out).group(1)
    return 'cp' + cp

def wpkggp_query(cp):
    msg = 'Query'
    out_msg = None
    try:
        pipeHandle = CreateFile("\\\\.\\pipe\\WPKG", GENERIC_READ | GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
    except pywintypes.error, (n, f, e):
        # print "Error when generating pipe handle: %s" % e
        out_msg = u"Error: WPKG-GP Service not running"
        return

    SetNamedPipeHandleState(pipeHandle, PIPE_READMODE_MESSAGE, None, None)
    WriteFile(pipeHandle, msg)
    packages = []
    n = 0
    #cp = 'cp1252'
    while 1:
        try:
            (hr, readmsg) = ReadFile(pipeHandle, 512)
            out = readmsg[4:]  # Strip 3 digit status code
            print repr(out)
            n += 1
            if n > 1:
                packages.append(out[7:].decode('utf-8').split('\t'))
            if out.startswith('Error') or out.startswith('Info'):
                out_msg = out

        except win32api.error as exc:
            if exc.winerror == winerror.ERROR_PIPE_BUSY:
                win32api.Sleep(5000)
                print 'Pipe Busy Error'
                continue
            break

    return packages, out_msg


cp = getActCP()
print cp

packages, error = wpkggp_query(cp)
print packages[0][0]

# Check if the query commands modifies the file date of wpkg.xml !
wpkgfile = "C:\Windows\Sysnative\wpkg.xml"
time = datetime.datetime.fromtimestamp(os.path.getmtime(wpkgfile))
print time
