# contains PeeWee database models (our ORM)

import os
import time
from urllib.parse import urlparse

import peewee
import playhouse
import psycopg2
from peewee import CharField, DateTimeField, IntegerField
from playhouse import signals
from playhouse.postgres_ext import *

# in case no DATABASE_URL is specified, default to Heroku
url = urlparse(
    "postgres://yaddqlhbmweddl:SxBfLvKcO9Vj2b3tcFLYvLcv9m@ec2-54-243-47-46.compute-1.amazonaws.com:5432/d520svb6jevb35")
if "DATABASE_URL" in os.environ:
    url = urlparse(os.environ["DATABASE_URL"])


if "HEROKU_DB" in os.environ:  # for Heroku to work
    url = urlparse(os.environ["HEROKU_DB"])

config = dict(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port,
    sslmode='require'
)

conn = PostgresqlExtDatabase(
    autocommit=True,
    autorollback=True,
    register_hstore=False,
    **config)


class BaseModel(signals.Model):
    """
    The following is the data within the schema:
        database_dict["UniqueID"] = UniqueID : int (Integer)
        database_dict["TIMESTAMP"] = TIMESTAMP : (DateTime)
        database_dict["Title"] = Title : (Text)
        database_dict["Authors"] = Authors : (Text)
        database_dict["Abstract"] = Abstract : (Text)
        database_dict["Reference"] = Reference : (Text)
        database_dict["PMID"] = PMID : (VarChar)
        database_dict["DOI"] = DOI : (VarChar)
        database_dict["NeuroSynthID"] = NeuroSynthID : (VarChar)
        database_dict["Experiments"] = Experiments : (Text)
        database_dict["Metadata"] = Metadata : (Text)
    """

    class Meta:
        database = conn

""" Updated models """

class Articles_updated(BaseModel):
    uniqueid = peewee.PrimaryKeyField()
    timestamp = DateTimeField(db_column='TIMESTAMP', null=True)
    authors = CharField(null=True)
    title = CharField(null=True)
    abstract = CharField(null=True)
    reference = CharField(null=True)
    pmid = CharField(null=True, unique=True)
    doi = CharField(null=True)
    neurosynthid = CharField(null=True)
    metadata = CharField(null=True)
    # Removed experiments = CharField(null=True)

    class Meta:
        db_table = 'articles_updated'

class Experiments_updated(BaseModel):
    experiment_id = peewee.PrimaryKeyField()
    title = CharField(null=True)
    caption = CharField(null=True, db_column="markBadTable")
    mark_bad_table = CharField(null=True)
    article_id = ForeignKeyField(
        Articles_updated,
        to_field='pmid',
        db_column="articleId"
    )
    class Meta:
        db_table = "experiments_updated"

class Locations_updated(BaseModel):
    x = peewee.IntegerField()
    y = peewee.IntegerField()
    z = peewee.IntegerField()
    z_score = peewee.IntegerField(db_column='zScore')
    experiment_id = peewee.ForeignKeyField(
        Experiments_updated,
        to_field='experiment_id',
        db_column='experimentID'
    )
    class Meta:
        db_table = "locations_updated"
        primary_key = CompositeKey("x","y","z","experiment_id")

class Tags_updated(BaseModel):
    name = peewee.CharField(null=True)
    ontology = peewee.CharField(null=True)
    agree = peewee.IntegerField(null=True)
    disagree = peewee.IntegerField(null=True)
    experiment_id = peewee.ForeignKeyField(
        Experiments_updated,
        to_field='experiment_id'
    )
    class Meta:
        db_table = 'tags_updated'
        primary_key = CompositeKey("name","experiment_id")


""" End Article Table Update"""




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
    # TODO: change capitalization of this column for consistency
    password = CharField(db_column='Password', null=True)
    emailaddress = CharField(null=True)
    userid = peewee.PrimaryKeyField()
    username = CharField(null=True)
    collections = CharField(null=True)

    class Meta:
        db_table = 'users'







