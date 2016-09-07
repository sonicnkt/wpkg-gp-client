##Overview
- [Introduction](#introduction)
- [Update Notifications](#updates)
- [Update System](#upgrade)
- [Erros during update](#error)
- [Credits](#credits)
- [License](#license)

<a name="introduction">
##Introduction
WPKG-GP Client is a graphical user interface which allows normal users without elevated rights to manually update their
system software. The application starts with automatically with the user logging and informs of pending updates as well as
giving the user a graphical feedback of the installing updates.

The Application is coded in Python/wxPython and relies on a [modification of WPKG-GP](https://github.com/sonicnkt/wpkg-gp/)
and [WPKG](https://wpkg.org/)for actual installing process in the background.

<a name="updates">
##Update Notifications
The application can inform the user in a time interval of pending updates for the installed software. This has to be 
configured by the system administrator.

Only updates for already installed packages are currently supported, there will be no notifications for new packages that 
were not installed before.

Because the update database for WPKG-GP Client is independent of the actual WPKG package database on the update server, 
it is possible that there are pending updates that the user wasn't informed about.

You can also manually check for pending updates by choosing the option __Check for updates__ from the context menu of 
the tray icon.

<a name="upgrade">
##Update System
Double-clicking the tray icon, selecting the option __System update__ or clicking on an update notification bubble opens
up the _System Update_ dialog from which you can start a manual update of the installed software packages.

__Attention:__
You should close all applications and save all open documents, applications can close without a warning during the 
update installations and even a full restart without further conformation is possible.

Current progress of the update process is displayed using a progress bar and a text field with the current task running.
Keep in mind that the progress bar only displays the progress of the whole update process and not the process of the
individual installations.

If the update process finishes it will be shown by a full progress bar and the information "WPKG Process Finished" in 
the current progress text field. You can display the details of tasks performed by using the "__LOG__"  option.

Some programs need a system restart to function correctly after the installation. In most cases this wont be forced and 
the current user will only be informed to restart their system. A new system update will be blocked until the system was
restarted.

You can select the option __Shutdown after update__ before and during the update process is running. 

If a reboot or shutdown was initiated this process can be canceled by selecting the option __Cancel shutdown__ from the 
tray icons context menu. 

<a name="error">
##Erros during update
If an error occurs during the system update process with the installation of a package an error log will be opened 
automatically withe the process finished. A configured shutdown won't be executed.

<a name="credits">
##Credits
__WPKG-GP Client__ was developed by _Nils Thiele_.

__Source Code:__

Project: wpkg-gp-client <https://github.com/sonicnkt/wpkg-gp-client/><br/>
Copyright (c) 2016 _Nils Thiele_.

Project: wpkg-gp modification <https://github.com/sonicnkt/wpkg-gp/><br/>
Copyright (c) 2016 _Nils Thiele_.

__WPKG-GP Client__ uses code of other opensource projects:

- Project: python-markdown2 <https://github.com/trentm/python-markdown2/>
    - Copyright (c) 2012 _Trent Mick_.
    - License ([MIT License](https://github.com/trentm/python-markdown2/blob/master/LICENSE.txt))
- Project: wpkg-gp <https://github.com/cleitet/wpkg-gp>
    - Copyright 2010, 2011 _The WPKG-GP team_
    - License (???)
- Project: WindowsNT Eventlog Code from [ActiveStates.com](http://docs.activestate.com/activepython/3.3/pywin32/Windows_NT_Eventlog.html)
    - Code Author: _John Nielsen_


__Translations:__

- spanish by _Julio San José Antolín_

<a name="license">
##License
MIT LICENSE??