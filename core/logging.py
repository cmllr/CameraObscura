# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

"""
This module contains logging functionality
"""

import time
from datetime import datetime
from os import listdir, stat
from os.path import isfile, join, isabs
from shutil import move
from jsonpickle import encode
from core import config
from flask import Request

EVENT_ID_STARTED = "obscura.sensor.started"
EVENT_ID_HTTP_REQUEST = "obscura.http.request"
EVENT_ID_LOGIN_SUCCESS = "obscura.http.login_success"
EVENT_ID_LOGIN_FAILED = "obscura.http.login_failed"
EVENT_ID_UPLOAD = "obscura.http.upload"


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
    selectedLogMethod = config.get_configuration_value("log", "method")
    # allow only whitelisted method calls
    if selectedLogMethod is not None and selectedLogMethod in ["json", "stdout"]:
        return globals()[selectedLogMethod](entry)

    return False


def stdout(entry: LogEntry) -> bool:
    """
    Protocol entry log into stdout
    parameters
        entry: the log entry to protocol
    returns
        Operation success
    """
    print(entry)
    return True

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
        remote_addr = str(request.remote_addr)
        user_agent = request.headers.get("User-Agent")
        get_string = request.args
        post_string = request.form
        return log(
            id,
            datetime.now(),
            message,
            is_error,
            remote_addr,
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
