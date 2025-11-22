# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

from core import logging
from datetime import datetime

"""
Main management entry point for http actions
"""

__all__ = [
    'authorize',
    'catchfile',
    'servefile',
    'sleep',
    'video'
]


def is_action_present(action: str):
    return action in __all__


def run(action, app, path, route, request):
    if is_action_present(action):
        modules = globals()
        if action in modules:
            return modules[action].run(app, path, route, request)
    return None
