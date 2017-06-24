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


# front page
class MainHandler(BaseHandler):
    def get(self):
        email = self.get_current_email()
        gh_user = self.get_current_github_user()
        print(gh_user)
        #Save user to database if logged in:
        try:  # handle failures in bulk_add
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
        self.render("static/html/index.html", title=email,
                    github_user=gh_user["name"], github_avatar=gh_user["avatar_url"],
                    queries=Articles.select().wrapped_count(), success=submitted,
                    failure=failure, registered=registered, pw=self.get_current_password())


# login page
class LoginHandler(BaseHandler):
    def get(self):
        self.render("static/html/login.html", message="None", title="", failure=0)

    def post(self):
        email = self.get_argument("email")
        password = self.get_argument("password").encode("utf-8")
        hasher=hashlib.sha1()
        hasher.update(password)
        password = hasher.hexdigest()[:52]
        if user_login(email, password):
            self.set_secure_cookie("email", email)
            self.set_secure_cookie("password", password)
            self.redirect("/")
        else:
            self.render("static/html/login.html", message="Invalid", title="", failure=1)


# log the user out
class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("email")
        self.clear_cookie("password")
        self.redirect("/")


# registration page
class RegisterHandler(BaseHandler):
    def get(self):
        self.render("static/html/register.html", title="", failure=0)

    def post(self): # TODO: make into a JSON API endpoint
        username = self.get_body_argument("name").encode('utf-8')
        email = self.get_body_argument("email").encode('utf-8')
        password = self.get_body_argument("password").encode('utf-8')
        if register_user(username, email, password):
            self.set_secure_cookie("email", email)
            hasher=hashlib.sha1()
            hasher.update(password)
            password = hasher.hexdigest()[:52]
            self.set_secure_cookie("password", password)
            self.redirect("/?registered=1")
        else:
            self.render("static/html/register.html", title="", failure=1)


# search page
class SearchHandler(BaseHandler):
    def get(self):
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        req = self.get_query_argument("req", "t")
        email = self.get_current_email()
        gh_user = self.get_current_github_user()
        self.render("static/html/search.html", query=q, start=start,
                    title=email, req=req, # parameters like "req" and "title" need to be renamed to reflect what their values are
                    github_user=gh_user["name"],
                    github_avatar=gh_user["avatar_url"])
    def post(self): #allows introduction of manual article
        pmid = self.get_argument("newPMID")
        print(pmid)



# Handler for the textbox to add a table of coordinates on view-article page
class AddTableTextBoxHandler(BaseHandler):
    def post(self):
        pmid = self.get_argument("pmid", "")
        vals = self.get_argument("values", "")
        if self.is_logged_in():
            add_table_through_text_box(pmid, vals)
        self.redirect("/view-article?id=" + pmid)


# Adds a custom user Tag to the database
class AddUserDataHandler(BaseHandler):
    def post(self):
        id = self.get_argument("pmid")
        user_tag = self.get_argument("values")
        print(user_tag)
        add_user_tag(user_tag, id) # TODO: needs to verify API key
        self.redirect("/view-article?id=" +id)


# view-article page
class ArticleHandler(BaseHandler):
    def get(self):
        articleId = -1
        try:
            articleId = self.get_query_argument("id")
        except:
            self.redirect("/")  # id wasn't passed; redirect to home page
        gh_user = self.get_current_github_user()
        self.render("static/html/view-article.html", id=articleId,
                    github_user=gh_user["name"], github_avatar=gh_user["avatar_url"],
                    email=self.get_current_email(), key=self.get_current_password()) # TODO: rename all of the "title"s to "email", and change the HTML templates accordingly

    def post(self):  # TODO: make its own endpoint; does not belong in this handler
        id = self.get_body_argument('id')
        email = self.get_current_email()
        values = ""

        try: # TODO: get rid of try/catch and write correctly
            values = self.get_body_argument("dbChanges")
            values = json.loads(values)  # z-values in dictionary
            print(values)
        except:
            pass
        if values:
            update_z_scores(id, email, values)
            self.redirect("/view-article?id=" + str(id))

# account page
class AccountHandler(BaseHandler):
    def get(self):
        if self.is_logged_in():
            email = self.get_current_email()
            user = self.get_current_user()
            self.render('static/html/account.html', title=self.get_current_email(), username=user, message="",
                        password=self.get_current_password())
        else:
            self.redirect("/register")

    def post(self): # TODO: make into a JSON API endpoint "change-username-password"
        hasher = hashlib.sha1()
        hasher2 = hashlib.sha1()
        newUsername = self.get_argument("newUserName")
        currPassword = self.get_argument("currentPassword").encode('utf-8')
        newPass = self.get_argument("newPassword").encode('utf-8')
        confirmPass = self.get_argument("confirmedPassword")
        name = self.get_current_email()
        user = self.get_current_user()
        hasher.update(currPassword)
        currPassword = hasher.hexdigest()
        username = self.get_current_email()

        """Checks for valid user entries"""
        if newUsername == None and currPassword == None:
            self.render('static/html/account.html', title=name, username=username, message="NoInfo")
        if newPass != confirmPass:
            self.render('static/html/account.html', title=name, username=username, message="mismatch")
        if currPassword != user.password:
            self.render('static/html/account.html', title=name, username=username, message="badPass")

        if newUsername:
            update = User.update(username=newUsername).where(User.emailaddress == name)
            update.execute()
        if newPass:
            hasher.update(newPass)
            newPass = hasher2.hexdigest()
            update = User.update(password=newPass).where(User.emailaddress == name)
            update.execute()
        self.redirect("/")


# contribute page
class ContributionHandler(BaseHandler):
    def get(self):
        name = self.get_current_email()
        gh_user = self.get_current_github_user()
        self.render('static/html/contribute.html', title=name,github_user=gh_user["name"], github_avatar=gh_user["avatar_url"])


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
class TableVoteUpdateHandler(BaseHandler): # TODO: what is element? also, make into a JSON API endpoint
    def post(self):
        element = self.get_argument("element")
        direction = self.get_argument("direction")
        table_num = self.get_argument("table_num")
        pmid = self.get_argument("id")
        column = self.get_argument("column")
        user = self.get_current_email()
        update_table_vote(element,direction,table_num,pmid,column,user)
        self.redirect("/view-article?id=" + pmid)

# save an article to a user's account
class SaveCollectionHandler(BaseHandler):
    def post(self):
        if self.is_logged_in():
            articles_encoded = self.request.arguments["articles[]"]  # TODO: look into "get_arguments" function
            collection_name = self.request.arguments["collection"][0].decode("utf-8")
            articles_decoded = []
            for a in articles_encoded:
                article = a.decode('utf-8')  # TODO: move save article operations to models.py
                User_metadata.insert(user_id=self.get_current_email(),
                                     article_pmid=article, collection=collection_name).execute()
        else:
            pass # TODO: what happens if a user is not logged in? needs to handle this case
            # self.redirect("/view-article?id=" + str(value))


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
        (r"/login", LoginHandler),
        (r"/register", RegisterHandler),
        (r"/logout", LogoutHandler),
        (r"/account", AccountHandler),
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
        (r"/add-user-data", AddUserDataHandler),
        (r"/update-table-vote", TableVoteUpdateHandler),
        (r"/remove-from-collection", DeleteFileHandler)
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
