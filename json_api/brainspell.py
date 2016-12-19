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
            self.write("No such user.")
        else:
            self.write("Logging you in...")

class RegisterHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/register.html")
    def post(self):
        username = self.get_body_argument("name")
        email = self.get_body_argument("email")
        password = self.get_body_argument("password")
        self.write("User created.")
        User.create(username = username, emailaddress = email, password = password)

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/login.html")
        
    def post(self):
        Name = self.get_argument("text")
        self.write(Name)

class SearchHandler(tornado.web.RequestHandler):
    def get(self):
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        self.render("static/html/search.html", query=q, start=start)

class ArticleHandler(tornado.web.RequestHandler):
    def get(self):
        articleId = -1
        try:
            articleId = self.get_query_argument("id")
        except:
            self.redirect("/") # id wasn't passed; redirect to home page
        self.render("static/html/view-article.html", id=articleId)

class SearchEndpointHandler(tornado.web.RequestHandler):
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

class RandomEndpointHandler(tornado.web.RequestHandler):
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



class ArticleEndpointHandler(tornado.web.RequestHandler):
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
        (r"/add-article", AddArticleHandler)
    ])

if __name__ == "__main__":
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port) # hosts on localhost:5000
    print("Running Brainspell at http://localhost:5000...")
    tornado.ioloop.IOLoop.current().start()

