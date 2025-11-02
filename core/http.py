# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

"""
This module http related functionality
"""


from datetime import datetime
from os.path import join, isfile, isdir, isabs, exists
import re
from jsonpickle import decode
from flask import Flask, request, abort, render_template, Response, Request
from werkzeug.exceptions import HTTPException
from core import config, logging, actions
from core.actions import *
from pathlib import Path
from urllib import parse
from typing import Dict, Tuple

app = Flask(__name__, template_folder=join(config.ROOT, "templates"))
app.config["CACHE_TYPE"] = "null"
app.url_map.strict_slashes = False
ROUTES = None
LASTROUTE = None


def parse_routes(file: str) -> Dict:
    """
    parses the JSON routes file.

    parameters:
        file: The file path to the routes.json file

    returns:
        The parsed routes.json
        Throws exception in case of file not found
    """
    content = ""
    try:
        with open(file, "r") as f:
            content = f.read()
    except FileNotFoundError as e:
        print(e)

    obj = decode(content)
    return obj  # type: ignore

@app.after_request
def add_header(response: Response):
    """
    Adds a header if the configured routes has some
    """
    route = LASTROUTE
    if route is not None:
        if "headers" in route:
            for key, value in route["headers"].items():
                response.headers[key] = value
    return response

@app.errorhandler(404)  # type: ignore
@app.errorhandler(403)  # type: ignore
def error_handler(e: HTTPException):
    """
    Render the 403 and 403 errors

    parameters:
        e the HTTPException

    returns:
        Render template. If template/<name>/404.html or template/<name>/403.html exists, these files are used.
    """
    code = e.code
    template = config.get_configuration_value("http", "template")
    if template is None:
        raise Exception("No template configured")
    template_path = join(str(template), f"{code}.html")
    full_template_path = join(config.ROOT, "templates", template_path)
    print(full_template_path)
    if not exists(full_template_path):
        template_path = f"{code}.html"
    return render_template(template_path), code

def _get_route(
    routes: Dict, path: str, request: Request
) -> Tuple[str, Dict ]:
    """
    From the given routes, find the matching route. When searching, the query string will be appended to look into the route.json keys.

    parameters:
        route: The routes to search in
        path: The path, as seen as the injected variable in handle_route (leading "/" will be omitted then)
        request: The flask request object
    
    returns:
        Either the selected route or, if no route matches and the root is wanted, the root route ("" key in routes.json)
    """
    selected_route: Dict | None = None
    selected_path: str | None = None
    for value in routes:
        needle = path + get_string(request)
        if path and path[0] != "." and value != "" and re.match(value, needle):
            selected_route = routes[value]
            selected_path = value
            break

    if selected_route is None and path == "":
        selected_route = routes[""]
        selected_path = ""

    return (selected_path, selected_route) # type: ignore

def _log_wrapper(id: str, message: str, request: Request, is_error: bool) -> bool:
    """
    Logs generic messages into the logfile

    parameters:
        id: The identifier for the message. See logging module for details.
        message: The message to log
        request: The flask request object
        is_eror: If the request is considered causing a response > 200
        
    """
    remote_addr = str(request.remote_addr)
    user_agent = request.headers.get("User-Agent")
    get_string = request.args
    post_string = request.form
    return logging.log(
        id,
        datetime.now(),
        message,
        is_error,
        remote_addr,
        useragent=user_agent,
        get=get_string,
        post=post_string,
    )

@app.route("/", defaults={"path": ""}, methods=["POST", "GET", "PUT", "DELETE"]) # type: ignore
@app.route("/<path:path>", methods=["POST", "GET", "PUT", "DELETE"]) # type: ignore
def handle_route(path):
    """
    Tries to execute a given route based on the path
    If no route matches. The root route ("") will be used.
    """
    global ROUTES
    global LASTROUTE
    global_request: Request = request
    
    selected_path, selected_route = _get_route(ROUTES, path, request) # type: ignore

    _log_wrapper(
        logging.EVENT_ID_HTTP_REQUEST,
        "{0} {1}".format(request.method, global_request.url),
        global_request,
        selected_route is None,
    )
    if selected_route is None:
        return abort(404)
    LASTROUTE = selected_route
    for action in selected_route["actions"]:
        result = actions.run(action, app, selected_path, selected_route, global_request)
        if result is not None and isinstance(result, bool) is False:
            return result
        
def get_string(requestObj) -> str:
    """
    Returns the HTTP GET string out of the given request
    """
    result = ""
    get = requestObj.query_string.decode("utf-8")
    if get == "":
        return result
    return "?" + get

def serve():
    """
    Start the server
    """
    global ROUTES
    template = config.get_configuration_value("http", "template")
    if template is None:
        raise Exception("No template is configured")

    routesFiles = join(config.ROOT, "templates", str(template), "routes.json")
    ROUTES = parse_routes(routesFiles)

    app.run(
        debug=config.get_configuration_value("honeypot", "debug"),
        host=str(config.get_configuration_value("http", "host")),
        port=int(str(config.get_configuration_value("http", "port"))),
    )
