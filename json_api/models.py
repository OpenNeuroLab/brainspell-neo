# contains PeeWee database models (our ORM)

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
from functools import reduce
import json

from peewee import DateTimeField, CharField, IntegerField

url = urlparse("postgres://yaddqlhbmweddl:SxBfLvKcO9Vj2b3tcFLYvLcv9m@ec2-54-243-47-46.compute-1.amazonaws.com:5432/d520svb6jevb35") # in case no DATABASE_URL is specified, default to Heroku
if "DATABASE_URL" in os.environ:
    url = urlparse(os.environ["DATABASE_URL"])

if "HEROKU_DB" in os.environ: # for Heroku to work
    url = urlparse(os.environ["HEROKU_DB"])

config = dict(
    database = url.path[1:],
    user = url.username,
    password = url.password,
    host= url.hostname,
    port= url.port,
    sslmode = 'require'
)

conn = PostgresqlExtDatabase(autocommit= True, autorollback = True, register_hstore = False, **config)

#You can enter information here something like User.create(___)
# TODO: what does the above comment mean?

#db.commit() to save the change
# TODO: and this comment? save what change?

class BaseModel(signals.Model):
    """
    The following is the data within the schema:
        database_dict["UniqueID"] = UniqueID : int (Integer?)
        database_dict["TIMESTAMP"] = TIMESTAMP : (DateTime?)
        database_dict["Title"] = Title : (Text)
        database_dict["Authors"] = Authors : (Text)
        database_dict["Abstract"] = Abstract : (Text)
        database_dict["Reference"] = Reference : (Text)
        database_dict["PMID"] = PMID : (VarChar)
        database_dict["DOI"] = DOI : (varChar)
        database_dict["NeuroSynthID"] = NeuroSynthID : (VarChar)
        database_dict["Experiments"] = Experiments : (Text)
        database_dict["Metadata"] = Metadata : (Text)
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
    # saved_articles= TextField(null=True) #TODO ADD THIS

    class Meta:
        db_table = 'users'


class User_metadata(BaseModel):
    metadata_id = peewee.PrimaryKeyField()
    user_id = CharField()
    article_pmid = CharField()
    collection = CharField()

    class Meta:
        db_table = 'user_metadata'


"""
Returns a list of relevant columns user wishes to search
Follows PubMed Labeling System:
    [au] indicates author
    [ALL] all fields
    [MH] Mesh terms: To be added
    [PMID]: Pubmed ID
    [TIAB]: Title/Abstract
"""

# TODO: move the following two functions to the appropriate file (doesn't belong in models.py)

# TODO: what does this do?
def generate_circle(coordinate): #Coordinate of form "-26,54,14"
    ordered = [int(x) for x in coordinate.split(",")][0:3] #Ignore z-score
    search_terms = []
    for i in range(len(ordered)):
        for j in range(-1,2,1):
            val = list(ordered)
            val[i] = val[i] + j
            search_terms.append(",".join([str(x) for x in val]))
    return search_terms

# TODO: what does this do?
def coactivation(coordinate): # Yields around 11,000 coordinates
    coordinate_sets = []
    search_circle = generate_circle(coordinate)
    for item in search_circle:
        val = Articles.select(Articles.experiments).where(
            Match(Articles.experiments, item)
        ).execute()
        for item in val:
            data_set = eval(item.experiments)
            for location_sets in data_set:
                if location_sets.get("locations"):
                    coordinate_sets.append(location_sets["locations"])
    return coordinate_sets
