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
        (r"/json/coordinates", CoordinatesEndpointHandler),  # TODO: add to API documentation on wiki
        (r"/json/random-query", RandomEndpointHandler),
        (r"/json/add-article", AddArticleEndpointHandler),
        (r"/json/set-article-authors", ArticleAuthorEndpointHandler),
        (r"/json/article", ArticleEndpointHandler),
        (r"/json/delete-row", DeleteRowEndpointHandler),
        (r"/json/split-table", SplitTableEndpointHandler),
        (r"/json/add-row", AddCoordinateEndpointHandler), # adds a single coordinate row to the end of an experiment table
        (r"/json/flag-table", FlagTableEndpointHandler), # TODO: add API documentation
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
        (r"/search-add", AddArticleFromSearchPageHandler), # TODO: rename to something more descriptive ("add-article-from-search-page")
    ], debug=True, **settings)


if __name__ == "__main__":
    tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient",
                                                 defaults={"allow_nonstandard_methods": True})
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port)  # runs at localhost:5000
    print("Running Brainspell at http://localhost:5000...")
    tornado.ioloop.IOLoop.current().start()
