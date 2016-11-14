import urllib

import tornado.httpserver
import tornado.ioloop
import tornado.web
import os
import sqlite3
import pymysql # will be using this as a search engine for the time being
import sqlalchemy as sql
from elasticsearch import Elasticsearch
from elasticsearch import Elasticsearch, RequestsHttpConnection
import certifi
import json
import peewee
import tornado
import psycopg2

### Relies on the MySQL Database

import os
import psycopg2
from urllib.parse import urlparse
from models import *

### End of MYSQL Setup

### POSTGRES SETUP


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/index.html")

class LoginHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/login.html")
        
    def post(self):
        Name = self.get_argument("text")
        self.write(Name)


class SearchHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/request.html")

    def post(self):
        self.set_header("Content-Type", "text/plain")
        database_dict = {}
        text = self.get_body_argument("text")
        results = article_search(text) # A list of all matches
        for article in results:
            database_dict = {}
            database_dict["UniqueID"] = article.uniqueid
            database_dict["TIMESTAMP"] = article.timestamp
            database_dict["Title"] = article.title
            database_dict["Authors"] = article.authors
            database_dict["Abstract"] = article.abstract
            database_dict["Reference"] = article.reference
            database_dict["PMID"] = article.pmid
            database_dict["DOI"] = article.doi
            database_dict["NeuroSynthID"] = article.neurosynthid
            database_dict["Experiments"] = article.experiments
            database_dict["Metadata"] = article.metadata
            break # Done for now to limit computation time and mass dumping onto page
        self.write(json.dumps(database_dict, sort_keys = True, indent = 4, separators = (',', ': ')))

        # for UniqueID,TIMESTAMP,Title,Authors,Abstract,Reference,PMID,DOI,NeuroSynthID,Experiments,Metadata in cur.fetchall():
        #     database_dict = {}
        #     database_dict["UniqueID"] = UniqueID
        #     database_dict["TIMESTAMP"] = TIMESTAMP
        #     database_dict["Title"] = Title
        #     database_dict["Authors"] = Authors
        #     database_dict["Abstract"] = Abstract
        #     database_dict["Reference"] = Reference
        #     database_dict["PMID"] = PMID
        #     database_dict["DOI"] = DOI
        #     database_dict["NeuroSynthID"] = NeuroSynthID
        #     database_dict["Experiments"] = Experiments
        #     database_dict["Metadata"] = Metadata
        # self.write(json.dumps(database_dict, sort_keys = True, indent = 4, separators = (',', ': ')))

def make_app():
    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'static')}),
        (r"/", MainHandler),
        (r"/search", SearchHandler),
        (r"/login", LoginHandler)
    ])

if __name__ == "__main__":
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port) # hosts on localhost:5000
    tornado.ioloop.IOLoop.current().start()

