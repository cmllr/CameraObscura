import time
from flask import Flask, Request
from core import config
from typing import Dict
from random import randint

def run(_: Flask, __: str, route: Dict, ___: Request):
    """
    Delay further modules for a given duration.

    parameters:
        route: The route object to use.

    route object:
        duration: The float seconds to delay next modules by.
        randomize: A boolean. If true, a random offset will be added to the duration, based on the formula duration/randint(1,10)
    """

    if not config.are_route_config_values_existing(
        route["sleep"], ["duration"]
    ):
        raise Exception("sleep module called without sleep configured")

    duration = float(route["sleep"]["duration"])
    if "randomize" in route["sleep"] and route["sleep"]["randomize"]:
        offset = randint(1, 10)
        offset_duration = duration/offset
        duration += offset_duration

    time.sleep(float(route["sleep"]["duration"]))
