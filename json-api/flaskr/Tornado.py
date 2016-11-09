import tornado.ioloop
import tornado.web
import os
import sqlite3
import pymysql # will be using this as a search engine for the time being
import sqlalchemy as sql

from elasticsearch import Elasticsearch
from elasticsearch import Elasticsearch, RequestsHttpConnection
#from requests_aws4auth import AWS4Auth
import certifi
import json
import peewee
import tornado

### Relies on the MySQL Database
"""
Commenting out for now, just to get Heroku working (there's no database online at the moment)
hostname = '192.168.99.100'
username = 'root'
password = 'beo8hkii'
database = 'brainspell'
myConnection = pymysql.connect(host = hostname, user = username, passwd = password, db = database)
"""
### End of MYSQL Setup

### POSTGRES SETUP


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/go", StoryHandler),
        (r"/about", AllExtras)
    ])

class AllExtras(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/html/login.html", title = "ShowAll")
    def post(self):
        Name = self.get_argument("text")
        self.write(Name)


class StoryHandler(tornado.web.RequestHandler):
    def get(self):
        # self.write('<html lang = "en"><body>'
        # '<h1>Please Provide search term</h1>'
        # '<h2>Query will be provided to database</h2>'
        # '<form action="/go" method="POST">'
        # '<input type="text" name="text">'
        # '<input type="submit" name="my-form" value="Send">'
        # '</form></body></html>')
        self.render("templates/text.html",title = "ShowAll")
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
        self.write(json.dumps(database_dict,  sort_keys = True, indent = 4, separators = (',', ': ')))


if __name__ == "__main__":
    app = make_app()
    app.listen(5000) # hosts on localhost:5000
    tornado.ioloop.IOLoop.current().start()

