#Load Config File

import sys
import os
import ConfigParser #https://wiki.python.org/moin/ConfigParserExamples

#Get Executable Path:
pathname = os.path.dirname(sys.argv[0])
path = os.path.abspath(pathname) + os.sep

Config = ConfigParser.ConfigParser()

# If config.ini cant be opened the program stops
if not Config.read(path + 'wpkg-gp_client.ini'):
    print "Can't open config file: {}wpkg-gp_client.ini".format(path)
    sys.exit()

# Prints available sections in config file
# print Config.sections()

#USAGE: LoadConfig('SECTION')['ENTRY']  - Entry always small
def LoadConfig(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

def LoadSetting(section, entry):
    try:
        SECTION = LoadConfig(section)
    except ConfigParser.NoSectionError:
        value = None
    else:
        try:
            value = SECTION[entry]
            try:
                value = int(value)
            except ValueError:
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value == "":
                    value = False
        except KeyError:
            value = None
    return value