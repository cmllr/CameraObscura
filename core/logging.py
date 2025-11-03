# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

"""
This module contains logging functionality
"""
from __future__ import annotations
import time
from datetime import datetime
from os import listdir, stat
from os.path import isfile, join, isabs
from shutil import move
from jsonpickle import encode
from core import config
from flask import Request
from abc import abstractmethod
import importlib
from random import randint

EVENT_ID_STARTED = "obscura.sensor.started"
EVENT_ID_HTTP_REQUEST = "obscura.http.request"
EVENT_ID_LOGIN_SUCCESS = "obscura.http.login_success"
EVENT_ID_LOGIN_FAILED = "obscura.http.login_failed"
EVENT_ID_UPLOAD = "obscura.http.upload"

GLOBAL_RANDOM_IP_DEBUG_ONLY = None # Debug mode: Use a random ip 

class LogEntry:
    def __init__(
        self,
        eventId: str,
        timestamp: datetime,
        message: str,
        isError: bool,
        src_ip: str,
        sensor: str,
        **kwargs
    ):
        self.eventId: str = eventId
        self.timestamp: datetime = timestamp
        self.message = message
        self.isError = isError
        self.src_ip = src_ip
        self.sensor = sensor
        self.kwargs = kwargs

    def __repr__(self):
        return "[{0}] {1}: {2} {3}@{4}".format(
            self.timestamp,
            self.eventId,
            self.message,
            self.src_ip,
            self.sensor,
        )


def log(
    eventId: str,
    timestamp: datetime,
    message: str,
    isError: bool,
    src_ip: str,
    **kwargs
) -> bool:
    """
    Logs an event
    """
    sensor = str(config.get_configuration_value("honeypot", "sensor"))
    entry = LogEntry(eventId, timestamp, message, isError, src_ip, sensor, **kwargs)

    do_stdout = bool(str(config.get_configuration_value("honeypot", "stdout")))
    if do_stdout:
        print(entry)
    
    json(entry)
    webhook_target = config.get_configuration_value("webhook", "target")
    if webhook_target:
        # check if event is excluded
        flavour = str(config.get_configuration_value("webhook", "flavour"))
        got = import_from(flavour, str(webhook_target))
        ignored_event_ids_raw = config.get_configuration_value("webhook", "exclude")
        
        ignored_event_ids = ignored_event_ids_raw.split(",") if ignored_event_ids_raw is not None  else [] # type: ignore

        if entry.eventId not in ignored_event_ids:
            got.do(entry)
    return False


def json(entry: LogEntry) -> bool:
    """
    Protocol entry into JSON
    parameters
        entry: the log entry to protocol
    returns
        Operation success
    """
    result = True
    content = log_entry_to_json(entry)
    path = get_log_filename()
    try:
        with open(path, "a") as f:
            f.write(content + "\n")
    except FileNotFoundError as e:
        print(e)
        result = False
    return result

def log_entry_to_json(log_entry: LogEntry) -> str:
    """
    Encodes the given log entry into a JSON string.

    parameters
        log_entry The log entry
    
    returns
        The log entry as JSON, using jsonpickle
    """
    raw = log_entry.__dict__
    if log_entry.kwargs != {}:
        for key, value in log_entry.kwargs.items():
            raw[key] = value

    del log_entry.kwargs

    return encode(log_entry, unpicklable=False) # type: ignore

def get_absolute_path(filename: str) -> str:
    """
    Get the absolute path of a given file, seen from the root dir

    parameters:
        filename: The filename/ relative path

    returns:
        The absolute path
    """
    if isabs(filename):
        return filename
    return join(config.ROOT, filename)

def get_log_filename() -> str:
    """
    gets the rotated filename, e. g. obscura.log.1

    parameters:
        log.path from the configuration
        log.timespan from the configuration
    """
    path = str(config.get_configuration_value("log", "path"))
    absolute_path = get_absolute_path(path)
    now = int(time.time())
    if isfile(absolute_path):
        modification = int(stat(absolute_path).st_mtime)
    else:
        modification = now - 1  # to trigger creation
    timespan = int(str(config.get_configuration_value("log", "timespan")))
    if modification + timespan < now:
        files = [name for name in listdir(".") if isfile(name) and path in name]
        suffix = len(files)
        move(absolute_path, absolute_path + "." + str(suffix))
    return absolute_path

def _get_ip(request: Request) -> str:
    """
    Get the client ip

    parameters:
        request: The original request to receive remote_addr from.
        Attention: if honeypot.debug is configured, a random address will be used instead.
    """
    debug = bool(str(config.get_configuration_value("honeypot", "debug")))
    if not debug:
        return str(request.remote_addr)
    
    # Use a random, standing IP to reuse for debug purposes
    global GLOBAL_RANDOM_IP_DEBUG_ONLY
    if GLOBAL_RANDOM_IP_DEBUG_ONLY is None:
        ip =  f"{randint(0,255)}.{randint(0,255)}.{randint(0,255)}.{randint(0,255)}"
        GLOBAL_RANDOM_IP_DEBUG_ONLY = ip
    return GLOBAL_RANDOM_IP_DEBUG_ONLY

def log_wrapper(id: str, message: str, request: Request | None, is_error: bool) -> bool:
    """
    Logs generic messages into the logfile

    parameters:
        id: The identifier for the message. See logging module for details.
        message: The message to log
        request: The flask request object
        is_eror: If the request is considered causing a response > 200
    returns:
        Bool if the entry was logged
    """

    if request:
         
        user_agent = request.headers.get("User-Agent")
        get_string = request.args
        post_string = request.form
        return log(
            id,
            datetime.now(),
            message,
            is_error,
            _get_ip(request),
            useragent=user_agent,
            get=get_string,
            post=post_string,
        )
    else:
        return log(
            id,
            datetime.now(),
            message,
            is_error,
            "",
            useragent="",
            get={},
            post={},
        )



class Webhook():
    def __init__(self, target) -> None:
        self._target = target
    @abstractmethod
    def do(self, entry: LogEntry):
        pass




def import_from(module_name: str, target: str) -> Webhook:
    module_name, class_name = module_name.rsplit(".", 1)
    _class = getattr(importlib.import_module(module_name), class_name)
    instance = _class(target)
    return instance
