#Installs
#pip install requests-aws4auth


#String of imports. Delete what's not useful later
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash, jsonify
import os
import sqlite3
import pymysql # will be using this as a search engine for the time being
import sqlalchemy as sql

from elasticsearch import Elasticsearch
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import certifi
import json
import tornado
from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import FallbackHandler,RequestHandler,Application
from tornado.httpserver import HTTPServer
import peewee


app = Flask(__name__)
app.config.from_object(__name__)

hostname = '192.168.99.100'
username = 'root'
password = 'beo8hkii'
database = 'brainspell'
# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'brainspell_sanitized.sql'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
myConnection = pymysql.connect(host = hostname, user = username, passwd = password, db = database)

host = 'brainspell-rds.camtj8eoxvnf.us-west-2.rds.amazonaws.com'
awsauth = AWS4Auth('AKIAJP5SGWZFTUIDIVQQ', '7cbziYaYSFfc30Xu+5SXoBnRcixhMKAOezSoX9jh', 'us-west-2a', 'es')
#awsauth = AWS4Auth('brainspell_admin', 'brainspell', 'us-west-2a', 'es')


es = Elasticsearch(
    hosts = [{'host': host, 'port': 3306}],
    http_auth = awsauth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)


@app.route('/database')
def database():
    return es.info()


# DATABASE CONNECTION;
def connect_db():  # Connecting with pymysql to local for now --> switch to elastic from amazon
    rv = pymysql.connect(host = hostname, user = username, passwd = password, db = database)
    return rv


def get_db():
    if not hasattr(g, ''):
        g.sqlite_db = connect_db
    return g.sqlite_db()


# @app.teardown_appcontext
# def close_db(error):
#     """Closes the database again at the end of the request."""
#     if hasattr(g, 'sqlite_db'):
#         g.close()

def init_db():
    return connect_db().cursor()


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')



@app.route('/')
def show_main():
    return 'Nothing'
    #flash('This screen will show one article to test database connection')
    # db = myConnection.cursor()
    # db.execute('Select UniqueID from Articles WHERE UniqueID = 3290')
    # for item in db.fetchall():
    #     return item

#Type in the name of any old html file and it will link;
@app.route('/about') #This links to all the old html code 
def about():
    return render_template('/html/article.html')

@app.route('/go')
def search():
    return render_template("text.html")


@app.route('/data', methods=['GET', 'POST'])
def post():
    database_dict = {}
    text = request.form['text']
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
    return json.dumps(database_dict,  sort_keys = True, indent = 4, separators = (',', ': '))


if __name__ == "__main__":
    app.debug = True
    app.run()
    """Running using Tornado """
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(5000)
    IOLoop.instance().start()

