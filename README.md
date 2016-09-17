# WPKG-GP - Client
WPKG-GP Client is a small **GUI** for my __wpkg-gp__ that resides in the system tray and allows normal users to perform a wpkg 
update using the wpkg-gp background service without a reboot as well as inform the user of new updates. 

As the development went on i had to add some new features to wpkg-gp that were missing in the original version. 

The Client __depends__ on my [**wpkg-gp modification**](https://github.com/sonicnkt/wpkg-gp).

It is written in Python 2.7 and relies on the [wxpython](https://wxpython.org/) (not phoenix) module for the gui part as well as [pywin32](https://sourceforge.net/projects/pywin32/) module for 
the communication with the wpkg-gp service, windows registry and event log access.

Precompiled x86 binaries (works on both x64 and x86) are provided on the [releases page](https://github.com/sonicnkt/wpkg-gp-client/releases).
No additional software has to be installed (Python Environment) except for wpkg-gp of course.

You can find [screenshots](https://github.com/sonicnkt/wpkg-gp-client/wiki/Installation-and-Usage#usage) and detailed instructions in the projects [Wiki](https://github.com/sonicnkt/wpkg-gp-client/wiki).
