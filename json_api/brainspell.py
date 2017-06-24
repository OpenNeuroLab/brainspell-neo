# handlers for the user-facing website, and the Tornado I/O loop

import urllib
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.httpclient
import os
import json
import peewee
import psycopg2
import tornado.escape
from models import *
import subprocess
import hashlib
from base64 import b64encode
from article_helpers import *
from json_api import *
from user_accounts import *
from github_collections import *
from article_helpers import *


# front page
class MainHandler(BaseHandler):
    def get(self):
        try: # handle failures in bulk_add
            submitted = int(self.get_argument("success", 0))
        except:
            submitted = 0
        try:
            failure = int(self.get_argument("failure", 0))
        except:
            failure = 0
        try:  # handle registration
            registered = int(self.get_argument("registered", 0))
        except:
            registered = 0

        custom_params = {
            "number_of_queries": Articles.select().wrapped_count(), # TODO: move to DAO (data access object)
            "success": submitted, # TODO: name these variables better (they refer to bulk_add success/failure)
            "failure": failure,
            "registered": registered # boolean that indicates if someone has just registered
        }

        self.render_with_user_info("static/html/index.html", custom_params)


# search page
class SearchHandler(BaseHandler):
    def get(self):
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        req = self.get_query_argument("req", "t")
        custom_params = {
            "query": q,
            "start": start,
            "req": req, # TODO: parameters like "req" and "title" need to be renamed to reflect what their values are)
        }
        self.render_with_user_info("static/html/search.html", custom_params)



class SearchAddEndpoint(BaseHandler):
    def post(self): #allows introduction of manual article
        pmid = self.get_argument("newPMID")
        getArticleData(pmid)


# Handler for the textbox to add a table of coordinates on view-article page
class AddTableTextBoxHandler(BaseHandler):
    def post(self):
        pmid = self.get_argument("pmid", "")
        vals = self.get_argument("values", "")
        if self.is_logged_in():
            add_table_through_text_box(pmid, vals)
        self.redirect("/view-article?id=" + pmid)


# Adds a custom user Tag to the database
class AddUserTagToArticleHandler(BaseHandler):
    def post(self):
        pmid = self.get_argument("pmid")
        user_tag = self.get_argument("values")
        add_user_tag(user_tag, pmid) # TODO: needs to verify API key
        self.redirect("/view-article?id=" + pmid)


# view-article page
class ArticleHandler(BaseHandler):
    def get(self):
        article_id = -1
        try:
            article_id = self.get_query_argument("id")
        except:
            self.redirect("/") # id wasn't passed; redirect to home page
        article_dict = {
            "article_id": article_id
        }
        self.render_with_user_info("static/html/view-article.html", article_dict)

    def post(self):  # TODO: make its own endpoint; does not belong in this handler
    # right now, this updates z scores
        article_id = self.get_body_argument('id')
        email = self.get_current_email()
        values = ""

        try: # TODO: get rid of try/catch and write correctly
            values = self.get_body_argument("dbChanges")
            values = json.loads(values)  # z-values in dictionary
            print(values)
        except:
            pass
        if values:
            update_z_scores(article_id, email, values)
            self.redirect("/view-article?id=" + str(article_id))

# contribute page
class ContributionHandler(BaseHandler):
    def get(self):
        self.render('static/html/contribute.html',
            github_name=self.get_current_github_name(), 
            github_avatar=self.get_current_github_avatar())

# takes a file in JSON format and adds the articles to our database (called from the contribute page)
class BulkAddHandler(BaseHandler):
    def post(self):
        file_body = self.request.files['articlesFile'][0]['body'].decode('utf-8')
        contents = json.loads(file_body)
        if type(contents) == list:
            clean_articles = clean_bulk_add(contents)
            add_bulk(clean_articles)
            self.redirect("/?success=1")
        else:
            # data is malformed
            self.redirect("/?failure=1")

# update a vote on a table tag
class TableVoteUpdateHandler(BaseHandler): # TODO: make into a JSON API endpoint
    def post(self):
        tag_name = self.get_argument("element")
        direction = self.get_argument("direction")
        table_num = self.get_argument("table_num")
        pmid = self.get_argument("id")
        column = self.get_argument("column")
        user = self.get_current_github_username()
        update_table_vote(tag_name, direction, table_num, pmid, column, user)
        self.redirect("/view-article?id=" + pmid)

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
        (r"/json/saved-articles", SavedArticlesEndpointHandler), # TODO: add API documentation
        (r"/json/delete-article", DeleteArticleEndpointHandler), # TODO: add API documentation
        (r"/json/toggle-user-vote", ToggleUserVoteEndpointHandler),
        (r"/search", SearchHandler),
        (r"/view-article", ArticleHandler),
        (r"/contribute", ContributionHandler),
        (r"/bulk-add", BulkAddHandler),
        (r"/add-table-text", AddTableTextBoxHandler),
        (r"/oauth", GithubLoginHandler),
        (r"/github_logout", GithubLogoutHandler),
        # (r"/save-collection", SaveCollectionHandler),
        # (r"/save-bulk",BulkNewFileHandler),
        (r"/repos", ReposHandler),
        (r"/create_repo", NewRepoHandler),
        (r"/add-to-collection", NewFileHandler),
        (r"/add-user-data", AddUserTagToArticleHandler),
        (r"/update-table-vote", TableVoteUpdateHandler),
        (r"/remove-from-collection", DeleteFileHandler),
        (r"/search-add",SearchAddEndpoint),
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
