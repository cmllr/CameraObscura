# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

"""
This module contains any logic to parse the config file
"""
import configparser
from os.path import dirname, abspath, join
from typing import Dict, List

CONFIG = None
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


def getConfiguration(cfgfile: str) -> object:
    """
    Read config
    @param cfgfile: filename of the file
    @return: ConfigParser object
    """
    parser = configparser.ConfigParser()
    if parser.read(cfgfile) is False:  # reading was not successfully
        return None
    return parser


def getConfigurationValue(section: str, key: str):
    """
    Get config value
    @param section: the section of the config value
    @param key: the config value name itself
    @return: the value or None, if not found
    """
    global CONFIG
    if CONFIG is None:  # config is empty
        CONFIG = getConfiguration(join(ROOT, "configuration.cfg"))

    if CONFIG is None:  # config is still empty -> failure
        return None

    if section in CONFIG and key in CONFIG[section]:
        value = CONFIG[section][key]
        if value == 'true' or value == 'false':
            return value == 'true'
        return CONFIG[section][key]

    return None
