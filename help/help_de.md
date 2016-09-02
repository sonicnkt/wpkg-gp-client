##Inhalt
- [Einleitung](#introduction)
- [Updates Benachrichtigungen](#updates)
- [System Aktualisieren](#upgrade)
- [Fehler bei der Aktualisierung](#error)
- [Credits](#credits)
- [Lizenz](#license)

<a name="introduction">
##Einleitung
WPKG-GP Client ist ein grafisches Benutzerinterface was es normalen System Benutzer (Ohne Administatoren Rechte)
ermöglich die Software auf ihrem System manuell zu aktualisieren. Der Prozess verläuft nach dem Start vollautomatisch
im Hintergrund und der Benutzer wird über die Fortschritt der Aktualisierung informiert.

Geschrieben ist das Programm in Python/wxPython und nutzt für die eigentlich Software Aktualisierung eine Modifikation
von [WPKG-GP](https://github.com/cleitet/wpkg-gp/wiki)

<a name="updates">
##Update Benachrichtigungen
Das Programm kann in einem vom System Administrator festgelegten Interval überprüfen ob Aktualisierungen für das System 
vorliegen und den angemeldeten Benutzer über diese Benachrichtigen.

Dabei wird jedoch nur neueren Versionen für bereits installierte Software-Pakete überprüft, Benachrichtigungen für
anstehende Neuinstallationen gibt es (noch) nicht.

Da die Updates-Datenbank unabhängig von der realen Paket Datenbank auf dem Update-Server ist kann es unter Umständen 
dazu kommen, dass es für bereits anstehende Updates noch keine Benachrichtigungen gibt.

Über das Kontext-Menü in der Taskleiste kann über die Option __Auf Updates prüfen__ eine manuelle Suche gestartet werden.

<a name="upgrade">
##System Aktualisieren
Per Doppelklick auf das Taskbar-Icon, die Option __Update System__ im Kontext-Menü oder der Klick auf eine Update
Benachrichtigung wird das Aktualisierungs Fenster geöffnet. Von hier aus kann eine manuelle System Aktualisierung
gestartet werden.

__Achtung:__
Alle Anwendungen sollten sicherheitshalber geschlossen werden und offene Dokumente gespeichert, da Programme ohne Vorwarnung 
während einer Aktualisierung geschlossen werden können. In Ausnahmefällen kann es sogar vorkommen, dass das komplette 
System ohne Benachrichtigung neustartet.

Der Aktuelle Fortschritt der Aktualisierung wird über einen Fortschrittsbalken und einem Textfeld (Aktueller Fortschritt)dargestellt, dieses stellt 
aber nur den Fortschritt des kompletten Aktualisierungs Vorgangs da und <u>NICHT</u> den Fortschritt der Installation der individuellen Software.

Der Prozess ist abgeschlossen wenn der Fortschrittsbalken komplett ist und unter _Aktueller Fortschritt_ "WPKG Process Finished" erscheint.
Über die Option "__LOG__" können Sie sich die durchgeführte Arbeiten im Detail aufführen lassen. 

Einige Programme benötigen nach der Aktualisierung einen Neustart des Systems um korrekt funktionieren zu können, dieser 
wird nicht automatisch durchgeführt, der Benutzer wird jedoch dazu aufgefordert. Eine erneute Aktualisierung wird zudem 
blockiert.

Vor und auch während einer Aktualisierung können Sie die Option __Nach Aktualisierung Herunterfahren__ aktivieren oder 
deaktivieren.

Wenn ein Neustart oder Herunterfahren initialisiert wurde kann dieser Prozess vom Benutzer abgebrochen werden über die 
Option __Herunterfahren Abbrechen__ im Kontext-Menü. Wieviel Zeit dafür bleibt wird vom Systemadministrator festgelegt.

<a name="error">
##Fehler bei der Aktualisierung
Falls es bei der Aktualisierung des Systems Fehler bei der Installation einzelner Pakete gegeben hat wird nach dem Abschluss der Aktualisierung
automatisch eine Fehlerprotokoll aufgerufen. Ein konfiguriertes Herunterfahren wird nicht ausgeführt.

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