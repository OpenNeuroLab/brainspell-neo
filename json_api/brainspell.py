# the Tornado I/O loop

import argparse
import os
import re

import tornado.escape
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.web

import github_collections
import user_interface
import json_api
import deploy
import base_handler
from websockets import *

# BEGIN: init I/O loop

public_key = "private-key"
if "COOKIE_SECRET" in os.environ:
    public_key = os.environ["COOKIE_SECRET"]
assert public_key is not None, "The environment variable \"COOKIE_SECRET\" needs to be set."

settings = {
    "cookie_secret": public_key,
    "login_url": "/oauth",
    "compress_response": True
}


def getJSONEndpoints():
    """
    Parse the JSON endpoints in json_api and create routes for the endpoint,
    and the endpoint's help page at /json/*/help.

    Use AbstractEndpoint to assert that the JSON endpoints are well-formed.
    """

    endpoints = []
    for name, func in [(convert(f.replace("EndpointHandler", "")), eval("json_api." + f))
                       for f in dir(json_api) if "EndpointHandler" in f] \
        + [(convert(f.replace("EndpointHandler", "")), eval("github_collections." + f))
            for f in dir(github_collections) if "EndpointHandler" in f]:
        endpoints.append((r"/json/" + name, func))
        endpoints.append((r"/json/" + name + "/", func))
        endpoints.append((r"/json/" + name + "/help", func))
        endpoints.append((r"/json/" + name + "/help/", func))
        base_handler.AbstractEndpoint.register(func)
    return endpoints


def getUserInterfaceHandlers():
    """ Parse the UI handlers and create routes. Assert that the route is specified. """
    handlers = []
    for func in [eval("user_interface." + f) for f in dir(user_interface)
                 if "Handler" in f and "EndpointHandler" not in f] \
        + [eval("github_collections." + f) for f in dir(github_collections)
            if "Handler" in f and "EndpointHandler" not in f]:
        if func is not base_handler.BaseHandler:
            assert func.route is not None, "The class " + \
                func.__name__ + " did not specify its route."
            handlers.append(("/" + func.route, func))
    return handlers


def make_app():
    """ Create a Tornado web application with routes """

    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'static')}),
        (r"/deploy", deploy.DeployHandler),
        (r"/api-socket", EndpointWebSocket),
    ] + getJSONEndpoints() + getUserInterfaceHandlers(), debug=True, **settings)


def get_port_to_run():
    """ Allow the user to specify a custom port by CLI """

    parser = argparse.ArgumentParser(description="Run Brainspell locally.")
    parser.add_argument(
        '-p',
        metavar="--port",
        type=int,
        help='a port to run the server on',
        default=5000)
    args = parser.parse_args()
    if args.p == 5000:
        port_to_run = int(os.environ.get("PORT", args.p))
    else:
        port_to_run = args.p
    return port_to_run


if __name__ == "__main__":
    tornado.httpclient.AsyncHTTPClient.configure(
        "tornado.curl_httpclient.CurlAsyncHTTPClient", defaults={
            "allow_nonstandard_methods": True})
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)

    port_to_run = get_port_to_run()

    http_server.listen(port_to_run)  # runs at localhost:5000 by default
    print("Running Brainspell at http://localhost:" + str(port_to_run) + "...")
    tornado.ioloop.IOLoop.current().start()
