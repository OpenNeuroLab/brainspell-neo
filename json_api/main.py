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

from urllib.parse import urlparse
from models import *

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/index.html")

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/login.html")
        
    def post(self):
        email = self.get_argument("email")
        password = self.get_argument("password")
        user = User.select().where(User.emailaddress == email and User.password == password)
        user = user.execute()
        if user == None:
            self.write("No such user")
        else:
            self.write("Logging you in")

class AddUser(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/user_entry.html")
    def post(self):
        username = self.get_body_argument("name")
        email = self.get_body_argument("email")
        password = self.get_body_argument("password")
        self.write("User Created")
        User.create(username = username, emailaddress = email, password = password)

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/login.html")
        
    def post(self):
        Name = self.get_argument("text")
        self.write(Name)

class SearchHandler(tornado.web.RequestHandler):
    def get(self):
        q = ""
        try:
            q = self.get_query_argument("q")
        except:
            pass # q wasn't passed; default to an empty string
        self.render("static/html/search.html", query=q)

class SearchEndpointHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        database_dict = {}
        q = self.get_query_argument("q")
        start = 0
        try:
            start = self.get_query_argument("start")
        except:
            pass # start wasn't passed; default to zero
        results = article_search(q, start)
        output_list = []
        for article in results:
            article_dict = {}
            article_dict["UniqueID"] = article.uniqueid
            article_dict["Title"] = article.title
            article_dict["Authors"] = article.authors
            output_list.append(article_dict)
        self.write(json.dumps(output_list))

def make_app():
    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'static')}),
        (r"/", MainHandler),
        (r"/query", SearchEndpointHandler),
        (r"/search", SearchHandler),
        (r"/login", LoginHandler),
        (r"/add-user", AddUser)
    ])

if __name__ == "__main__":
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port) # hosts on localhost:5000
    tornado.ioloop.IOLoop.current().start()

