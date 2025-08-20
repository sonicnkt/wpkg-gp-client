# -*- encoding: utf-8 -*-
# WPKG-GP Client BUILD SCRIPT

VERSION = "0.9.8.4"         # max 4 number values separated by a "."
NAME = "WPKG-GP Client"     # Application Name
AUTHOR = "Nils Thiele"
PYTHONSHELL = False         # True or False, If True the compiled exe includes console window
INSTALLER = True            # True or False, If True innosetup installer will be created
INNOSETUPCMD = '%PROGRAMFILES(X86)%\Inno Setup 6\iscc.exe'             # InnoSetup with PreProcessor Support!

# DO NOT MODIFY AFTER THIS POINT IF YOU DON'T KNOW WHAT YOU ARE DOING!!!

print('WPKG-GP Client Build script')
print('___________________________\n')
print("Version: ", VERSION)
print("Name: ", NAME)
print("Author: ", AUTHOR)
print("ISCC path: ", INNOSETUPCMD)
print("Python Shell: ", str(PYTHONSHELL))

from datetime import datetime
import os, sys
import codecs
import re

pathname = os.path.dirname(sys.argv[0])
path = os.path.abspath(pathname) + os.sep
BUILDID = VERSION + '-' + datetime.strftime(datetime.now(), '%Y%m%d')

version_txt = '''VSVersionInfo(ffi=FixedFileInfo(
    filevers=({0}),
    prodvers=({0}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '000004b0',
        [StringStruct('Comments', '{1}'),
        StringStruct('LegalCopyright', '\xa9{2}'),
        StringStruct('CompanyName', './.'),
        StringStruct('FileDescription', '{1}'),
        StringStruct('FileVersion', '{3}'),
        StringStruct('ProductVersion', '{3}'),
        StringStruct('InternalName', '{1}'),
        StringStruct('LegalTrademarks', '{1} is a Trademark of {2}.'),
        StringStruct('OriginalFilename', 'WPKG-GP-Client.exe'),
        StringStruct('ProductName', '{1}'),
        StringStruct('BuildID', '{4}')])
      ]),
    VarFileInfo([VarStruct('Translation', [0, 1200])])
  ]
)
'''

def v_convert(ver_str):
    # Converts any version string to a 4 digit string seperated by ", ".
    if len(ver_str) > 0:
        ver = ver_str.split('.')
        if len(ver) > 4:
            ver = [num for f, num in enumerate(ver) if f < 4]
        elif len(ver) < 4:
            add = 4 - len(ver)
            for _ in range(0, add):
                ver.append('0')
        new_ver_str = ' ,'.join(ver)
        return new_ver_str
    else:
        print("Error: You have to specify a correct version value!\n")
        sys.exit(1)

# Changing current working directory for pyinstaller
os.chdir(path)
print('Changed current working directory to: ', os.getcwd())

print()
print('Clean up directories...')
print('-----------------------')
# remove old dist directory
rmdir_cmd = 'rmdir "{}" /s /q'.format(os.path.join(path, 'dist', 'WPKG-GP-Client'))
os.system(rmdir_cmd)

print()
print('Creating SPEC file...')
print('---------------------')
# Create version.txt file for pyinstaller, spec file
current_version_txt = version_txt.format(v_convert(VERSION), NAME, AUTHOR, VERSION, BUILDID)
with codecs.open(path + 'version.txt', 'w', 'utf-8') as outfile:
    outfile.write(current_version_txt)
# Create pyinstaller spec file for this build
with codecs.open('WPKG-GP Client.spec', 'r', 'utf-8') as spec_input:
    spec_file = spec_input.read()
# switch console window on/off
current_spec_file = re.sub(r'console=(True|False),', 'console=' + str(PYTHONSHELL) + ',', spec_file)
with codecs.open(path + '{}.spec'.format(BUILDID), 'w', 'utf-8') as outfile:
    outfile.write(current_spec_file)


print()
print('Starting Pyinstaller...')
print('-----------------------')
# run pyinstaller
pyinstaller_cmd = 'pyinstaller -y "{}.spec"'.format(BUILDID)
os.system(pyinstaller_cmd)

if os.path.isdir(os.path.join(path, 'dist', 'WPKG-GP-Client')):
    # Copy Help Files and example ini to build directory
    os.system('xcopy "{0}" "{1}\" /S /E /I /H'.format(
        os.path.join(path, 'help'),
        os.path.join(path, 'dist', 'WPKG-GP-Client', 'help'),
        ))
    os.system('xcopy "{0}" "{1}\" /I /H'.format(
        os.path.join(path, 'wpkg-gp_client_example.ini'),
        os.path.join(path, 'dist', 'WPKG-GP-Client'),
        ))
    print()
    print('Pyinstaller process successful.')
    print()
    # going forward
else:
    print('Error Occurred during pyinstaller process')
    sys.exit(1)

if INSTALLER:
    print('Building Inno Setup installer...')
    print('--------------------------------')
    # running inno setup to create installer package
    INNOSETUPPATH = os.path.expandvars(INNOSETUPCMD)
    if PYTHONSHELL:
        installer_name = 'wpkg-gp-client_v' + VERSION + '_debug'
    else:
        installer_name = 'wpkg-gp-client_v' + VERSION
    innosetup_cmd = '""' + INNOSETUPPATH + '"' + ' /DMyOutput="{0}" /DMyAppVersion={1} /DMyAppName="{2}" ' \
                                                 '/DMyAppPublisher="{3}" /DMySourceDir="{4}" "{5}""'.format(
                                                                            installer_name,
                                                                            VERSION,
                                                                            NAME,
                                                                            AUTHOR,
                                                                            os.path.join(path, 'dist'),
                                                                            os.path.join(path, 'dist', "setup_script.iss"))
    os.system(innosetup_cmd)

