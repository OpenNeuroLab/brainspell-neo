# the Tornado I/O loop

import argparse
import os
import re

import tornado.escape
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.web

import json_api
from deploy import *
from github_collections import *
from user_interface_handlers import *
from web_sockets import *

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
    and the endpoint's help page at /json/*/help
    """

    endpoints = []
    for endpoint in [f for f in dir(json_api) if "EndpointHandler" in f]:
        func = eval("json_api." + endpoint)
        name = convert(endpoint.replace("EndpointHandler", ""))
        endpoints.append((r"/json/" + name, func))
        endpoints.append((r"/json/" + name + "/help", func))
    return endpoints


def make_app():
    """ Create a Tornado web application with routes """

    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'static')}),
        (r"/", MainHandler),
        (r"/search", SearchHandler),
        (r"/view-article", ViewArticleHandler),
        (r"/contribute", ContributionHandler),
        (r"/bulk-add", BulkAddHandler),
        (r"/deploy", DeployHandler),
        (r"/api-socket", EndpointWebSocket),
        # GitHub endpoints; TODO: change to a JSON API
        (r"/oauth", GithubLoginHandler),
        (r"/github-logout", GithubLogoutHandler),
        (r"/repos", ReposHandler),
        (r"/create_repo", NewRepoHandler),
        (r"/add-to-collection", NewFileHandler),
        (r"/remove-from-collection", DeleteFileHandler)
    ] + getJSONEndpoints(), debug=True, **settings)


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
