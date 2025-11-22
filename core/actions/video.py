# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

"""
Serves a given file as HTTP response
"""
from datetime import datetime
from posixpath import join
from typing import Dict
from flask import Flask, request, Response, Request, make_response
from core import config
from core.actions.servefile import run as serve_file
import pathlib
from os.path import isfile
from core.logging import log_wrapper, EVENT_ID_FFMPEG_STARTED
import subprocess
from shlex import split
def run(_: Flask, __: str, route: Dict, request: Request):    
    if "video" not in route["video"]:
        raise Exception("Video file missing")    
    
    if "mode" not in route["video"]:
        raise Exception("No mode selected")
    
    mode = route["video"]["mode"]
    if mode != "m3u8":
        raise Exception(f"Invalid mode supplied: {mode}")
    
    video_file = route["video"]["video"]

    file_info = pathlib.Path(video_file)


    video_file_name = file_info.name.replace(file_info.suffix, "")

    output_file = f"ul/{video_file_name}.m3u8"
    lock_file = f"ul/{video_file_name}.lock"

    if not isfile(lock_file):
        command_line = f"ffmpeg -loglevel quiet -stream_loop -1 -i {video_file} -filter:v fps=15 -s 720x480 -codec:v h264  -an -map 0 -f hls -hls_time 10 -hls_list_size 3 -hls_delete_threshold 3  -hls_flags delete_segments {output_file}"
        args = split(command_line)
        got = subprocess.Popen(args, stdout=None, stderr=None)

        with open(lock_file, "w+") as file:
            file.write(f"{got.pid}")

        
        log_wrapper(EVENT_ID_FFMPEG_STARTED, f"Started ffmpeg process with PID {got.pid}", None, False)

    return serve_file(  
        _,
        "",
        {
            "servefile": {
                "process_placeholder":  False,
                "process_template":  False,
                "file": output_file
            }
        },
        request,
    )