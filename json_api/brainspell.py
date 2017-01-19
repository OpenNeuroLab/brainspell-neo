import urllib

import tornado.httpserver
import tornado.ioloop
import tornado.web
import os
import certifi
import json
import peewee
import tornado
import psycopg2
import tornado.escape
from models import *
import subprocess

"""Handles User Login Requests"""
class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

class MainHandler(BaseHandler):
    def get(self):
        if not self.current_user:
            self.render("static/html/index.html", title="")
        else:
            name = tornado.escape.xhtml_escape(self.current_user)
            self.render("static/html/index.html", title=name)

class LoginHandler(BaseHandler):
    def get(self):
        self.render("static/html/login.html", message="None")
        
    def post(self):
        email = self.get_argument("email")
        password = self.get_argument("password")
        user = User.select().where(User.emailaddress == email and User.password == password)
        user = user.execute()
        if user.count == 0:
            self.render("static/html/login.html", message="Invalid")
        else:
            self.set_secure_cookie("user",email)
            self.redirect("/")

class RegisterHandler(BaseHandler):
    def get(self):
        self.render("static/html/register.html")
    def post(self):
        username = self.get_body_argument("name")
        email = self.get_body_argument("email")
        password = self.get_body_argument("password")
        self.write("User created.")
        User.create(username = username, emailaddress = email, password = password)


class SearchHandler(BaseHandler):
    def get(self):
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        self.render("static/html/search.html", query=q, start=start)

class AddArticleHandler(BaseHandler):
    def get(self):
        pass

class ArticleHandler(BaseHandler):
    def get(self):
        articleId = -1
        try:
            articleId = self.get_query_argument("id")
        except:
            self.redirect("/") # id wasn't passed; redirect to home page
        self.render("static/html/view-article.html", id=articleId)

class SearchEndpointHandler(BaseHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        database_dict = {}
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
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


class ArticleEndpointHandler(BaseHandler):
    def get(self):
        id = self.get_query_argument("id")
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

settings = {
    "cookie_secret": os.environ["COOKIE_SECRET"],
    "login_url": "/login",
}

def make_app():
    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'static')}),
        (r"/", MainHandler),
        (r"/query", SearchEndpointHandler),
        (r"/random-query", RandomEndpointHandler),
        (r"/search", SearchHandler),
        (r"/login", LoginHandler),
        (r"/register", RegisterHandler),
        (r"/article", ArticleEndpointHandler),
        (r"/view-article", ArticleHandler),
        (r"/add-article", AddArticleHandler),
        (r"/viewer", TranslucentViewerHandler)
    ], **settings, debug=True)

if __name__ == "__main__":
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port) # hosts on localhost:5000
    print("Running Brainspell at http://localhost:5000...")
    tornado.ioloop.IOLoop.current().start()

