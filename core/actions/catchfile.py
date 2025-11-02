# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

from os.path import join, isdir, isfile
from datetime import datetime
from core import config, logging
from flask import Flask, Request, abort
from typing import Dict


def run(_: Flask, __: str, ___: Dict, request_obj: Request):
    """
    Catch uploaded files. Relies on the downloadDir setting.

    For each requewst bringing files following files will be created

    - {hash}_{post_field} - The uploaded file(s)
    - report_{hash}.txt - The Report for this request, listing all collected files with original filename, stored filename, size, content type.

    parameters:
        request_obj: The Flask request object

    route object:
        There are no options.
    
    returns:
        404 abort if: File object is None, Download directory is unconfigured, Download directory does not exist.
    
    """
    report_content = ""
    report_filename = None
    for key, file_object in request_obj.files.items():
        if not file_object:
            return abort(404)
        filename = f"{request_obj.__hash__()}_{key}"
        
        download_dir = config.get_configuration_value("honeypot", "downloadDir")

        if not download_dir:
            return abort(404)
        
        absolute_download_dir = join(config.ROOT, str(download_dir))

        if not isdir(absolute_download_dir):
            return abort(404)
        
        if report_filename is None:
            # we can assume that there is a proper download dir now
            report_filename = join(absolute_download_dir, f"report_{request_obj.__hash__()}.txt")

        file_path = join(absolute_download_dir, filename)
        file_object.save(file_path)

        report_content += f"Filename: {file_object.filename}\n" + f"Stored filename: {filename}\n"+  f"Size: {file_object.content_length}\n" + f"Type: {file_object.content_type}\n" + "\n"
        
        logging.log(
            logging.EVENT_ID_UPLOAD,
            datetime.now(),
            f"Uploaded file with report {report_filename}",
            not isfile(file_path),
            str(request_obj.remote_addr),
        )
    # only write a report if there were files
    if report_filename is not None:
        with open(report_filename, "w") as file:
            file.write(report_content)
