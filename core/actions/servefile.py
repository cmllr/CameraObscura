# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

"""
Serves a given file as HTTP response
"""

import random
import re
from datetime import datetime
from os.path import join
import pathlib
from flask import Flask, request, send_file, render_template, Request, abort
from core import config, http
from PIL import ImageDraw, Image
from typing import Dict
from time import strftime


def _replace_placeholders(text: str) -> str:
    """
    Replace placeholders from the given text.

    Placeholders are hereby two set of replacements:
        - strftime() format placeholders for date and time - These are prefixed with a % symbol
        - placeholders of this project - These are prefixed with a $ symbol and represent configuration.cfg values. Therefore they follow the format $section.setting

    parameters:
        text: The text containing the Python date time variables, see the params fro strftime() for details

    returns:
        A string with the replaced values
        If the text is none an empty string is returned
    """
    if text is None:
        return ""
    # first go: Replace date and time placeholders.
    text = strftime(text)
    # second go: Replace internal placeholders
    placeholder_matches = re.findall(r"(\$[a-z\.]+)", text)
    if placeholder_matches is not None:
        for match in placeholder_matches:
            name = match.replace("$", "")

            # Format must be $honeypot.setting_name
            if "." in name:
                parts = name.split(".")
                value = config.get_configuration_value(parts[0], parts[1])
                if type(value) == str:
                    text = text.replace(match, value)
    return text

def _apply_watermark(watermark_obj: Dict, file_path: str) -> str:
    """
    Apply a watermark to the given file path and store it in a new file name.

    The method will create file.jpg -> file_tmp.jpg and overwrite, if needed.

    parameters:
        watermark_obj: The Dictionary of the watermark configuration inside routes.json
        file_path: The file to apply the watermark onto
    returns:
        A string representing the new absolute file path
        If the file does not exist, an Exception is thrown
        If parameters in the watermark_obj are missing, an Exception is thrown
    """

    if not config.are_route_config_values_existing(
        watermark_obj, ["x", "y", "color", "text"]
    ):
        raise Exception(
            "At least one of following configuration values are missing: x, y, color, text"
        )

    x_coord = watermark_obj["x"]
    y_coord = watermark_obj["y"]
    colors = watermark_obj["color"]
    text = watermark_obj["text"]

    # Get the new path
    path = pathlib.Path(file_path)
    if not path.exists:
        raise Exception("The image to be watermarked does not exist")

    extension = path.suffix
    file_name = path.name.replace(extension, "")

    new_file_name = f"{file_name}_tmp{extension}"
    new_file_path = join(path.parent.absolute(), new_file_name)

    # Add the required text, maybe with date time placeholders
    text = _replace_placeholders(text)

    with Image.open(file_path) as im:
        draw = ImageDraw.Draw(im)
        draw.text((x_coord, y_coord), text, tuple(colors))  # Coordinates
        format = im.format
        im.save(new_file_path + "", format)
    return new_file_path

def _key_pattern_forward(route_key: str, request_path: str, file: str) -> str | None:
    """
    If the key of a route is considered a regex, process a file path correspondingly.

    parameters:
        route_key: The key of the route
        request_path: The request path from Flask
        file: The file to alter. When the file contains $<number>, replacement of the group from the route_key is attempted. Files are always seen as files inside the root directory of the software.

    example:
        route_key: images/(.+)
        file: files/$1.jpg
        request_path: images/foo/bar/barz.png
        Returned value will be files/foo/bar/barz.png
    
    returns:
        If the file does not exist, None is returned
        The new file path, otherwise. If now replacements are done, it's the value from the file parameter
    """
    match = re.search(route_key, request.path)
    if match is not None:
        groups = match.groups()
        index = 1
        for group in groups:
            file = file.replace("$" + str(index), group)
            index = index + 1

    # Return none to be able to throw it as a 404 later
    path = pathlib.Path(config.ROOT, file)
    if not path.exists():
       return None
    return file

def run(_: Flask, route_key: str, route: Dict, request: Request):
    """
    Serve a file.

    parameters:
        route_key: The path key from the routes.json configuration
        route: The route object
        request: The Flask Request itself

    route object:
        if file is an array, a random value will be processed further.
        if the key of the route contains a set of round brackets "()", it is considered as a regex to match a sub path file. See _key_pattern_forward() for details
        if process_template is set, the file is considered as a template and will be fowarded to a render_template call.
        if process_placeholders is set, the file is considered a (plain) text file with replacements. See _replace_placeholders() for details
        if watermark is set, the file is considered an image file and needs watermark text to be applied. See _apply_watermark() for details
    
    returns:
        If "file" is missing inside the route config, an exception is thrown
    """
    if "file" not in route["servefile"]:
        raise Exception("File missing for serve file route.")
    
    file = route["servefile"]["file"]

    if isinstance(file, list):
        random.seed(datetime.now().time().microsecond)
        file = file[random.randint(0, len(file) - 1)]
    
    regex_key = "(" in route_key
    # Regex route params handling
    if regex_key:
        file = _key_pattern_forward(route_key, request.path, file)
        if not file:
            return abort(404)
    
    file_to_serve = join(config.ROOT, file)
    process_template = (
        "process_template" in route["servefile"]
        and route["servefile"]["process_template"]
    )
    if process_template:
        get_values = http.getString(request)
        return render_template(
            file.replace("templates/", ""), # JInja2 expects the file already being in "templates"
            config=config,
            getValues=get_values,
            ip=request.remote_addr,
        )

    process_placeholders = (
        "process_placeholders" in route["servefile"]
        and route["servefile"]["process_placeholders"]
    )
    if process_placeholders:
        content = ""
        with open(file_to_serve, "r") as handle:
            content = handle.read()
            content = _replace_placeholders(content)
        return content

    watermark = "watermark" in route["servefile"]
    if watermark:
        new_file_path = _apply_watermark(route["servefile"]["watermark"], file_to_serve)
        response = send_file(new_file_path, as_attachment=False, download_name="image")
        return response
    return send_file(file_to_serve, as_attachment=False)
