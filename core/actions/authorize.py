# Copyright (c) 2018 RoastingMalware
# See the LICENSE file for more information

"""
Receives the username and password from a login request
"""
from datetime import datetime
from urllib import parse
from flask import Flask, request, Request, abort, redirect
from core import logging, config
from typing import Dict, List


def _is_authorized(username: str, password: str, user_db: str) -> bool:
    success = False
    with open(user_db, "r") as file:
        lines = file.readlines()
        for line in lines:
            parts = line.split(";", 1)
            db_username = parts[0]
            db_password = parts[1]
            if db_username == username and db_password == password:
                success = True
                break
    return success


def run(_: Flask, __: str, route: Dict, request: Request):
    """
    Attempt to authorize a user. On error, the user is either shown a status code or been redirected already.

    On success, the module just let the next module execute
    
    parameters:
      route: The route dictionary
      request: The Flask route
    
    route object:
      key_username: The key to search in POST and GET for the username
      key_password: The key to search in POST and GET for the password
      user_db: The userdb to use. The default userdb.txt can be used. It's an CSV file. Please do not use ";" in usernames
      on_error: Either an status code or route key to redirect to
    """
    if "authorize" not in route:
        raise Exception("Authorize action options missing")

    if not config.are_route_config_values_existing(
        route["authorize"], ["key_username", "key_password"]
    ):
        return abort(403)

    key_username = route["authorize"]["key_username"]
    key_password = route["authorize"]["key_password"]

    get = request.args
    query_string = request.query_string.decode("utf-8")
    # if the query_string is an %-encoded query string (contains %3) -> Reparse the string to get the dictionary
    # Flask seems not to unquote them and puts the complete query string as a key into the request.args dictionary, which is hard to log
    if "%3" in query_string:
        unquoted = parse.unquote(query_string)
        get_params = parse.parse_qs(unquoted)
        get = get_params

    post = request.form

    # Search for the matching keys in POST and GET
    username = None
    password = None
    haystacks: List[Dict] = [get, post]
    for haystack in haystacks:
        username = haystack.get(key_username)
        password = haystack.get(key_password)

        if username is not None and password is not None:
            break

    if username and password:
        if "user_db" not in route["authorize"]:
            raise Exception("User DB not configured")

        is_authorized = _is_authorized(
            username, password, route["authorize"]["user_db"]
        )
        logging.log(logging.EVENT_ID_LOGIN,
                  datetime.now(),
                  "Login attempt [{0}/{1}] {2}".format(username, password, "failed" if not is_authorized else "succeeded"),
                  False,
                  str(request.remote_addr),
                  username=username, password=password)
        
        if not is_authorized:
          if "on_error" not in route["authorize"]:
              return abort(403)
          on_error = route["authorize"]["on_error"]

          if isinstance(on_error, int):
            # an return code is wanted
            return abort(on_error)
          else:
            # a route redirect is wanted
            return redirect(on_error)