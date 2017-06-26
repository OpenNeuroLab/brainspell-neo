# the Tornado I/O loop

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.httpclient
import os
import tornado.escape
from json_api import *
from github_collections import *
from user_interface_handlers import *
from deploy import *
import argparse

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

def make_app():
    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'static')}),
        (r"/", MainHandler),
        (r"/json/query", SearchEndpointHandler),
        # TODO: add to API documentation on wiki
        (r"/json/coordinates", CoordinatesEndpointHandler),
        (r"/json/random-query", RandomEndpointHandler),
        (r"/json/add-article", AddArticleEndpointHandler),
        (r"/json/set-article-authors", ArticleAuthorEndpointHandler),
        (r"/json/article", ArticleEndpointHandler),
        (r"/json/delete-row", DeleteRowEndpointHandler),
        (r"/json/split-table", SplitTableEndpointHandler),
        # adds a single coordinate row to the end of an experiment table
        (r"/json/add-row", AddCoordinateEndpointHandler),
        # TODO: add API documentation
        (r"/json/flag-table", FlagTableEndpointHandler),
        (r"/json/bulk-add", BulkAddEndpointHandler),
        (r"/json/toggle-user-vote", ToggleUserVoteEndpointHandler),
        (r"/search", SearchHandler),
        (r"/view-article", ArticleHandler),
        (r"/contribute", ContributionHandler),
        (r"/bulk-add", BulkAddHandler),
        (r"/add-table-text", AddTableTextBoxHandler),
        (r"/oauth", GithubLoginHandler),
        (r"/github_logout", GithubLogoutHandler),
        # (r"/save-bulk",BulkNewFileHandler),
        (r"/repos", ReposHandler),
        (r"/create_repo", NewRepoHandler),
        (r"/add-to-collection", NewFileHandler),
        (r"/add-user-data", AddUserTagToArticleHandler),
        (r"/update-table-vote", TableVoteUpdateHandler),
        (r"/remove-from-collection", DeleteFileHandler),
        # TODO: rename to something more descriptive
        # ("add-article-from-search-page")
        (r"/search-add", AddArticleFromSearchPageHandler),
        (r"/deploy", DeployHandler)
    ], debug=True, **settings)


if __name__ == "__main__":
    tornado.httpclient.AsyncHTTPClient.configure(
        "tornado.curl_httpclient.CurlAsyncHTTPClient", defaults={
            "allow_nonstandard_methods": True})
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)

    # allow the user to specify a custom port by CLI
    parser = argparse.ArgumentParser(description="Run Brainspell locally.")
    parser.add_argument('-p', metavar="--port", type=int, help='a port to run the server on', default=5000)
    args = parser.parse_args()
    if args.p == 5000:
        port_to_run = int(os.environ.get("PORT", args.p))
    else:
        port_to_run = args.p

    http_server.listen(port_to_run)  # runs at localhost:5000 by default
    print("Running Brainspell at http://localhost:" + str(port_to_run) + "...")
    tornado.ioloop.IOLoop.current().start()
