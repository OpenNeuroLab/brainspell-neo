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


conn = psycopg2.connect(
    database= 'd520svb6jevb35',
    user= 'yaddqlhbmweddi',
    password= 'SxBfLvKcO9Vj2b3tcFLYvLcv9m',
    host= 'ec2-54-243-47-46.compute-1.amazonaws.com',
    port= '5432',
)
print(conn)


# hostname = 'ec2-54-243-47-46.compute-1.amazonaws.com'
# username = 'yaddqlhbmweddi'
# password = 'SxBfLvKcO9Vj2b3tcFLYvLcv9m'
# database = 'd520svb6jevb35'
#
# myConnection = psycopg2.connect(host = hostname, user = username, password = password, database = database)

print(conn)
### End of MYSQL Setup

### POSTGRES SETUP


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/front/index.html")

class AllExtras(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/login.html", title = "ShowAll")
        
    def post(self):
        Name = self.get_argument("text")
        self.write(Name)


class StoryHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("static/html/text.html")

    def post(self):
        self.set_header("Content-Type", "text/plain")
        database_dict = {}
        text = self.get_body_argument("text")
        cur = myConnection.cursor()
        cur.execute("ALTER TABLE Articles ADD FULLTEXT(Title)")
        search_string = "Select UniqueID,TIMESTAMP,Title,Authors,Abstract,Reference, PMID, DOI, NeuroSynthID, Experiments, Metadata" \
                        " from Articles WHERE match (Title) against ('%{0}%' IN NATURAL LANGUAGE MODE)".format(text)
        cur.execute(search_string)
        for UniqueID,TIMESTAMP,Title,Authors,Abstract,Reference,PMID,DOI,NeuroSynthID,Experiments,Metadata in cur.fetchall():
            database_dict = {}
            database_dict["UniqueID"] = UniqueID
            database_dict["TIMESTAMP"] = TIMESTAMP
            database_dict["Title"] = Title
            database_dict["Authors"] = Authors
            database_dict["Abstract"] = Abstract
            database_dict["Reference"] = Reference
            database_dict["PMID"] = PMID
            database_dict["DOI"] = DOI
            database_dict["NeuroSynthID"] = NeuroSynthID
            database_dict["Experiments"] = Experiments
            database_dict["Metadata"] = Metadata
        self.write(json.dumps(database_dict, sort_keys = True, indent = 4, separators = (',', ': ')))

def make_app():
    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'static')}),
        (r"/", MainHandler),
        (r"/go", StoryHandler),
        (r"/about", AllExtras)
    ])

if __name__ == "__main__":
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port) # hosts on localhost:5000
    tornado.ioloop.IOLoop.current().start()

