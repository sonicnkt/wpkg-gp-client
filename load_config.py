import ConfigParser  # https://wiki.python.org/moin/ConfigParserExamples


class NoConfigFile(Exception):
    pass


class ConfigIni:
    def __init__(self, configfile):
        self.config = ConfigParser.ConfigParser()
        if not self.config.read(configfile):
            error_str = "NoConfigFile Error - Can't open config file:\n{}".format(configfile)
            raise NoConfigFile(error_str)

    def _loadsection(self, section):
        dict1 = {}
        options = self.config.options(section)
        for option in options:
            try:
                dict1[option] = self.config.get(section, option)
                if dict1[option] == -1:
                    print("skip: %s" % option)
            except:
                print("exception on %s!" % option)
                dict1[option] = None
        return dict1

    def loadsetting(self, section, entry):
        # section always lowercase
        try:
            section = self._loadsection(section)
        except ConfigParser.NoSectionError:
            value = None
        else:
            try:
                value = section[entry]
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
