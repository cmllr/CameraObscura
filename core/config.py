# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

"""
This module contains any logic to parse the config file
"""
import configparser
from os.path import dirname, abspath, join
from typing import Dict, List

CONFIG: Dict | None = None
ROOT = dirname(dirname(abspath(__file__)))


def are_route_config_values_existing(haystack: Dict, needles: List) -> bool:
    """
    Helper function to check if there are keys in a dictionary missing, e. g. for route values

    parameters:
        haystack: An flat dictionary containing the key value pairs to check
        needles: The keys to search for

    returns:
        If haystack is None, False is returned
        If one of the keys is missing, False is returned
        If all keys were found, True is returned
    """
    if haystack is None:
        return False
    for needle in needles:
        if needle not in haystack:
            return False

    return True


def get_configuration(cfg_file: str) -> Dict | None:
    """
    Get the system config

    parameters:
        cfg_file: The config file path.

    returns:
        The dictionary containing the configuration
        None if the file does contain a valid configuration
    """
    parser = configparser.ConfigParser()
    if parser.read(cfg_file) is False:  # reading was not successfully
        return None
    return dict(parser)


def get_configuration_value(section: str, key: str):
    """
    Get config value
    parameters:
        section: The [section] to search in
        key: The key to search for

    returns:
        The value of the configuration or None on error.
    """
    global CONFIG
    if CONFIG is None:  # config is empty
        CONFIG = get_configuration(join(ROOT, "configuration.cfg"))
    if CONFIG is None:  # config is still empty -> failure
        return None

    if section in CONFIG and key in CONFIG[section]:
        value = CONFIG[section][key]
        if value == "true" or value == "false":
            return value == "true"
        return CONFIG[section][key]

    return None
