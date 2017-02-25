import peewee
import psycopg2
from playhouse import signals
import time
import peewee
import os
from urllib.parse import urlparse
import playhouse
import hashlib
from playhouse.postgres_ext import *
import re

from peewee import DateTimeField, CharField, IntegerField
# urlparse.uses_netloc.append("postgres")
url = urlparse("postgres://yaddqlhbmweddl:SxBfLvKcO9Vj2b3tcFLYvLcv9m@ec2-54-243-47-46.compute-1.amazonaws.com:5432/d520svb6jevb35")
if "DATABASE_URL" in os.environ:
    url = urlparse(os.environ["DATABASE_URL"])

config = dict(
    database = url.path[1:],
    user = url.username,
    password = url.password,
    host= url.hostname,
    port= url.port,
    sslmode = 'require'
)

#print(config)
#Now using extDatabase for PostGres full text search
conn = PostgresqlExtDatabase(autocommit= True, autorollback = True, register_hstore = False, **config) #used to be peewee.PostgresqlDatabase
#print(conn)

#You can enter information here something like User.create(___)

#db.commit() to save the change

class BaseModel(signals.Model):
    """
    The Following is the data within the schema
        database_dict["UniqueID"] = UniqueID --> int (Integer?)
        database_dict["TIMESTAMP"] = TIMESTAMP --> (DateTime?)
        database_dict["Title"] = Title --> (Text)
        database_dict["Authors"] = Authors --> (Text)
        database_dict["Abstract"] = Abstract --> (Text)
        database_dict["Reference"] = Reference --> (Text)
        database_dict["PMID"] = PMID --> (VarChar)
        database_dict["DOI"] = DOI --> (varChar)
        database_dict["NeuroSynthID"] = NeuroSynthID --> (VarChar)
        database_dict["Experiments"] = Experiments --> (Text)
        database_dict["Metadata"] = Metadata --> (Text)
    """
    class Meta:
        database = conn


class Articles(BaseModel):
    timestamp = DateTimeField(db_column='TIMESTAMP', null=True)
    abstract = CharField(null=True)
    authors = CharField(null=True)
    doi = CharField(null=True)
    experiments = CharField(null = True)
    metadata = CharField(null=True)
    neurosynthid = CharField(null=True)
    pmid = CharField(null=True, unique=True)
    reference = CharField(null=True)
    title = CharField(null=True)
    uniqueid = peewee.PrimaryKeyField()

    class Meta:
        db_table = 'articles'

class Concepts(BaseModel):
    name = CharField(db_column='Name', null=True)
    definition = CharField(null=True)
    metadata = CharField(null=True)
    ontology = CharField(null=True)
    uniqueid = peewee.PrimaryKeyField()

    class Meta:
        db_table = 'concepts'

class Log(BaseModel):
    data = CharField(db_column='Data', null=True)
    timestamp = DateTimeField(db_column='TIMESTAMP', null=True)
    type = CharField(db_column='Type', null=True)
    experiment = IntegerField(null=True)
    pmid = CharField(null=True)
    uniqueid = peewee.PrimaryKeyField()
    username = CharField(null=True)

    class Meta:
        db_table = 'log'

class User(BaseModel):
    password = CharField(db_column='Password', null=True)
    emailaddress = CharField(null=True)
    userid = peewee.PrimaryKeyField()
    username = CharField(null=True)

    class Meta:
        db_table = 'users'

"""
Returns a list of relevant columns user wishes to search
Follows PubMed Labeling System:
    [au] indicates author
    [ALL] all fields
    [MH] Mesh terms --> To be added
    [PMID] --> Pubmed ID
    [TIAB] --> Title/Abstract
"""
def parse(query):
    columns = []
    au = re.compile(r"\[au]")
    all = re.compile(r"\[ALL]")
    mesh = re.compile(r"\[MH]")
    pmid = re.compile(r"\[PMID]")
    tiab = re.compile(r"\[TIAB]")
    if au.search(query):
        columns.append(Articles.authors)
    if all.search(query):
        columns.extend([Articles.timestamp, Articles.abstract,
                        Articles.authors, Articles.doi,
                        Articles.experiments, Articles.metadata,
                        Articles.neurosynthid, Articles.pmid,
                        Articles.reference,Articles.title])
    if mesh.search(query):
        columns.append(Articles.metadata)
    if pmid.search(query):
        columns.append(Articles.pmid)
    if tiab.search(query):
        columns.extend([Articles.title, Articles.abstract])
    return columns

def formatted_search(query,start,param=None):
    if not param:
        query = query.replace(" ", "%")
        columns = parse(query)
        if not columns: #Implement default parameters
            columns.extend([Articles.title, Articles.abstract, Articles.authors])
        formatted = [(x, query) for x in columns]
        formatted = ["Match" + str(x) for x in formatted]
        formatted = " | ".join(formatted)
        search = Articles.select(*columns).where(
            formatted).limit(10).offset(start)
        return search.execute()
    else:
        if param == "t":
            pass
        if param == "x":
            pass
        if param == "p":
            pass
        if param == "r":
            pass

def article_search(query, start):
    query = query.replace(" ", "%")
    search = Articles.select(Articles.pmid, Articles.title, Articles.authors).where(
        Match(Articles.title, query) | Match(Articles.authors, query) | Match(Articles.abstract, query)
    ).limit(10).offset(start)
    # return (search.count(), search.limit(10).offset(start).execute()) # give the total number of results, and output ten results, offset by "start"
    return search.execute() # search.count() makes the above line slow; TODO: find a better way of doing this

def random_search():
    search = Articles.select(Articles.pmid, Articles.title, Articles.authors).order_by(fn.Random()).limit(5)
    return search.execute()

def get_article(query):
    search = Articles.select().where(Articles.pmid == query)
    return search.execute()

def insert_user(user, pw, email):
    q = User.create(username = user, password = pw, emailaddress = email)
    q.execute()
    
def get_user(user):
    q = User.select().where(User.emailaddress==user)
    return q.execute()

def add_bulk(papers, limit=100): # Papers is the entire formatted data set
    with conn.atomic():
        for article in range(0,len(papers), limit): # Inserts limit at a time
            Articles.insert_many(papers[article:article+limit]).execute()


def user_login(email,password):
        hasher=hashlib.md5()
        hasher.update(password)
        password = hasher.hexdigest()
        user = User.select().where((User.emailaddress == email) & (User.password == password))
        return user.execute()

def register_user(username,email,password):
        hasher=hashlib.md5()
        hasher.update(password)
        password = hasher.hexdigest()
        User.create(username = username, emailaddress = email, password = password)