import urllib

import tornado.httpserver
import tornado.ioloop
import tornado.web
import os
import json
import peewee
import tornado
import psycopg2
import tornado.escape
from models import *
import subprocess
import hashlib

from get_article_data import *

"""Handles User Login Requests"""
class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

class MainHandler(BaseHandler):
    def get(self):
        name = tornado.escape.xhtml_escape(self.current_user) if self.current_user else ""
        try:
            submitted = int(self.get_argument("success", 0))
        except:
            submitted = 0
        try:
            failure = int(self.get_argument("failure", 0))
        except:
            failure = 0
        self.render("static/html/index.html", title=name, 
            queries=Articles.select().wrapped_count(), success=submitted,
            failure=failure)

class LoginHandler(BaseHandler):
    def get(self):
        self.render("static/html/login.html", message="None", title="")

    def post(self):
        email = self.get_argument("email")
        password = self.get_argument("password").encode("utf-8")
        user = user_login(email,password)
        if user.count == 0:
            self.render("static/html/login.html", message="Invalid", title="")
        else:
            self.set_secure_cookie("user", email)
            self.redirect("/")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect("/")


class RegisterHandler(BaseHandler):
    def get(self):
        self.render("static/html/register.html", title="")
    def post(self):
        username = self.get_body_argument("name")
        email = self.get_body_argument("email")
        password = self.get_body_argument("password")
        register_user(username,email,password)
        self.redirect("/login")


class SearchHandler(BaseHandler):
    def get(self):
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        req = self.get_query_argument("req", "t")
        name = tornado.escape.xhtml_escape(self.current_user) if self.current_user else ""
        self.render("static/html/search.html", query=q, start=start,
            title=name, req=req)

class AddArticleEndpointHandler(BaseHandler):
    """def post(self):
        pmid = self.get_query_argument("pmid", "")
        if pmid == "":
            pmid = self.get_body_argument("pmid")
        x = getArticleData(pmid)
        request = Articles.insert(abstract=x["abstract"],doi=x["DOI"],authors=x["authors"],
                                  experiments=x["coordinates"],title=x["title"])
        request.execute()
        response = {"success": 1}
        self.write(json.dumps(response))
    get = post"""
    def get(self):
        pmid = self.get_query_argument("pmid", "")
        x = getArticleData(pmid)
        request = Articles.insert(abstract=x["abstract"],doi=x["DOI"],authors=x["authors"],
                                  experiments=x["coordinates"],title=x["title"])
        request.execute()
        response = {"success": 1}
        self.write(json.dumps(response))


class ArticleHandler(BaseHandler):
    def get(self):
        articleId = -1
        try:
            articleId = self.get_query_argument("id")
        except:
            self.redirect("/") # id wasn't passed; redirect to home page
        self.render("static/html/view-article.html", id=articleId,
            title=tornado.escape.xhtml_escape(self.current_user) if self.current_user else "")


class SearchEndpointHandler(BaseHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        database_dict = {}
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        option = self.get_query_argument("req", "t")
        results = article_search(q, start)
        response = {}
        output_list = []
        for article in results:
            article_dict = {}
            article_dict["id"] = article.pmid
            article_dict["title"] = article.title
            article_dict["authors"] = article.authors
            output_list.append(article_dict)
        response["articles"] = output_list
        if len(results) == 0:
            response["start_index"] = -1
            # returns -1 if there are no results;
            # UI can always calculate (start, end) with (start_index + 1, start_index + 1 + len(articles))
            # TODO: consider returning the start/end indices for the range of articles returned instead
        else:
            response["start_index"] = start
        self.write(json.dumps(response))

class RandomEndpointHandler(BaseHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        database_dict = {}
        results = random_search()
        response = {}
        output_list = []
        for article in results:
            article_dict = {}
            article_dict["id"] = article.pmid
            article_dict["title"] = article.title
            article_dict["authors"] = article.authors
            output_list.append(article_dict)
        response["articles"] = output_list
        self.write(json.dumps(response))

class TranslucentViewerHandler(BaseHandler):
    def get(self):
        cmd = "python translucent.py"
        subprocess.call(cmd, shell=True)

class AccountHandler(BaseHandler):
    def get(self):
        name = tornado.escape.xhtml_escape(self.current_user) if self.current_user else ""
        user = next(get_user(name))
        username = user.username
        self.render('static/html/account.html', title=name, username=username, message="")

    def post(self):
        hasher=hashlib.md5()
        hasher2 = hashlib.md5()
        newUsername = self.get_argument("newUserName")
        currPassword = self.get_argument("currentPassword").encode('utf-8')
        newPass = self.get_argument("newPassword").encode('utf-8')
        confirmPass = self.get_argument("confirmedPassword")
        name = tornado.escape.xhtml_escape(self.current_user) if self.current_user else ""
        user = next(get_user(name))
        username = user.username
        hasher.update(currPassword)
        currPassword = hasher.hexdigest()

        """Checks for valid user entries"""
        if newUsername == None and currPassword==None:
            self.render('static/html/account.html', title=name, username=username, message="NoInfo")
        if newPass != confirmPass:
            self.render('static/html/account.html', title=name, username=username, message="mismatch")
        if currPassword != user.password:
            self.render('static/html/account.html', title=name, username=username, message="badPass")

        if newUsername:
            update = User.update(username = newUsername).where(User.emailaddress == name)
            update.execute()
        if newPass:
            hasher.update(newPass)
            newPass = hasher2.hexdigest()
            update = User.update(password = newPass).where(User.emailaddress == name)
            update.execute()
        self.redirect("/")
class ContributionHandler(BaseHandler):
    def get(self):
        name = tornado.escape.xhtml_escape(self.current_user) if self.current_user else ""
        self.render('static/html/contribute.html',title=name)

class ArticleEndpointHandler(BaseHandler):
    def get(self):
        id = self.get_query_argument("pmid")
        article = next(get_article(id))
        response = {}
        response["timestamp"] = article.timestamp
        response["abstract"] = article.abstract
        response["authors"] = article.authors
        response["doi"] = article.doi
        response["experiments"] = article.experiments
        response["metadata"] = article.metadata
        response["neurosynthid"] = article.neurosynthid
        response["pmid"] = article.pmid
        response["reference"] = article.reference
        response["title"] = article.title
        response["id"] = article.uniqueid
        self.write(json.dumps(response))

class BulkAddHandler(tornado.web.RequestHandler):
    def post(self):
        # get post data
        file_body = self.request.files['articlesFile'][0]['body'].decode('utf-8')
        contents = json.loads(file_body)
        if type(contents) == list:
            for article in contents:
                try:
                    if "timestamp" not in article:
                        article["timestamp"] = None
                    articles["authors"] = ",".join(articles["authors"])
                    if "doi" not in article:
                        article["doi"] = None
                    if "experiments" in article:
                        article["experiments"] = str(article["experiments"])
                    else:
                        article["experiments"] = str([])
                    if "meshHeadings" in article:
                        article["metadata"] = str({"meshHeadings": article["metadata"]})
                        del article["meshHeadings"]
                    else:
                        article["metadata"] = str({"meshHeadings": []})
                    if "journal" in article and "year" in article:
                        article["reference"] = article["authors"] + "(" + article["year"] + ") " + article["journal"]
                        del article["journal"]
                        del article["year"]
                    else:
                        article["reference"] = None
                except:
                    pass
            add_bulk(contents)
            self.redirect("/?success=1")
        else:
            self.redirect("/?success=0")

public_key = "private-key"
if "COOKIE_SECRET" in os.environ:
    public_key = os.environ["COOKIE_SECRET"]
assert public_key is not None, "The environment variable \"COOKIE_SECRET\" needs to be set."

settings = {
    "cookie_secret": os.environ["COOKIE_SECRET"],
    "login_url": "/login",
    "compress_response":True
}

def make_app():
    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'static')}),
        (r"/", MainHandler),
        (r"/json/query", SearchEndpointHandler),
        (r"/json/random-query", RandomEndpointHandler),
        (r"/search", SearchHandler),
        (r"/login", LoginHandler),
        (r"/register", RegisterHandler),
        (r"/json/article", ArticleEndpointHandler),
        (r"/view-article", ArticleHandler),
        (r"/json/add-article", AddArticleEndpointHandler),
        (r"/logout", LogoutHandler),
        (r"/account", AccountHandler),
        (r"/contribute", ContributionHandler),
        (r"/bulk-add", BulkAddHandler)
    ], debug=True, **settings)

if __name__ == "__main__":
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port) # hosts on localhost:5000
    print("Running Brainspell at http://localhost:5000...")
    tornado.ioloop.IOLoop.current().start()

