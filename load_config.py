import configparser  # https://wiki.python.org/moin/ConfigParserExamples


class NoConfigFile(Exception):
    pass


class ConfigIni:
    def __init__(self, configfile):
        self.config = configparser.ConfigParser()
        if not self.config.read(configfile):
            error_str = "NoConfigFile Error - Can't open config file:\n{}".format(configfile)
            raise NoConfigFile(error_str)

    def load_section(self, section):
        """
        Loads all options and their values from the given section of the config file.
        Returns a dictionary with option names as keys and their values as strings.
        If an option cannot be read, None is stored for that option.

        Args:
            section (str): The section name to load.

        Returns:
            dict: A mapping of option names to their config values or None.
        """
        values = {}
        try:
            # Get all option names in the specified section
            options = self.config.options(section)
        except Exception as e:
            print(f"Could not retrieve options for section '{section}': {e}")
            return values  # Return empty dict if section is missing or unreadable

        for option in options:
            try:
                # Try to read the value for each option
                value = self.config.get(section, option)
                values[option] = value
                # Optionally skip or warn about values with specific invalid content
                if value == '-1':
                    print(f"Warning: Option '{option}' in section '{section}' has a value of '-1'.")
            except Exception as e:
                # Log exception and store None for this option
                print(f"Exception when reading option '{option}' in section '{section}': {e}")
                values[option] = None

        return values

    def load_setting(self, section, entry, expected_type=str, default=None):
        """
        Retrieves a config value and returns it converted to the expected_type,
        or the default value if it does not exist or conversion fails.

        Args:
            section (str): Section name in the config file.
            entry (str): Entry (option) name to look up.
            expected_type (type): The desired Python type for return value (e.g., int, bool, str).
            default: Value to return if the section/entry does not exist or conversion fails.

        Returns:
            The requested config value, converted to expected_type if possible,
            otherwise the given default value.
        """
        try:
            # Load whole section as a dictionary
            sectiondict = self.load_section(section)
            # Try to access the value for the given entry
            value = sectiondict[entry]
        except (KeyError, configparser.NoSectionError):
            # If section or entry is missing, return the default value
            return default

        if expected_type == int:
            # Try to convert the value to an integer
            try:
                return int(value)
            except (TypeError, ValueError):
                # Conversion failed, return default value
                return default
        elif expected_type == bool:
            # Convert various truthy strings to boolean True, everything else to False
            return str(value).strip().lower() in ('true', 'yes', 'on', '1')
        else:
            # For str or any other types, return the value as-is
            return value
