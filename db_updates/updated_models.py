# contains PeeWee database models (our ORM)
import os
import time
from urllib.parse import urlparse
import peewee
from playhouse import signals
from playhouse.postgres_ext import *

"""
Note naming conventions based on _updated tag are temporary
and indicate updated tables
"""

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
    # Storing mesh fields as [{value:<value>,agree:INT,disagree:INT},{...},...]
    mesh_tags = BinaryJSONField(null=True, db_column='meshTags')
    # metadata = CharField(null=True) # Replacing Charfield with JSONFIELD above
    # Removed experiments = CharField(null=True)

    class Meta:
        db_table = 'articles_updated'


class Experiments_updated(BaseModel):
    experiment_id = peewee.PrimaryKeyField(null=True)
    title = CharField(null=True)
    caption = CharField(null=True)
    mark_bad_table = BinaryJSONField(null=True, db_column="markBadTable")
    article_id = ForeignKeyField(
        Articles_updated,
        to_field='pmid',
        db_column="articleId"
    )
    num_subjects = peewee.IntegerField(null=True)
    space = peewee.CharField(null=True)
    # Storing mesh fields as [{name:<value>,agree:INT,disagree:INT}]
    mesh_tags = BinaryJSONField(null=True, db_column='meshTags')

    class Meta:
        db_table = "experiments_updated"


class Locations_updated(BaseModel):
    x = peewee.IntegerField()
    y = peewee.IntegerField()
    z = peewee.IntegerField()
    z_score = peewee.IntegerField(db_column='zScore', null=True)
    experiment_id = peewee.ForeignKeyField(
        Experiments_updated,
        to_field='experiment_id',
        db_column='experimentID'
    )

    class Meta:
        db_table = "locations_updated"
        primary_key = CompositeKey("x", "y", "z", "experiment_id")


"""
Votes updated represents user votes on experiment specific fields

Our usage currently supports two kinds of voting:
    Experiment based voting
        - This kind of voting requires a Composite Key to userid, name, and experimentID
         - A vote on an experiment is uniquely identified by:
            - The user voting: userid
            - The tag the user votes on: name
            - The experiment that contains the tag: experimentID
    Article based voting
        - This kind of voting requires a userid, name, and articleID rather than an experiment ID
        - Because all experiments are contained within an Article we add an additional parameter for articles
    There exists a uniqueness constraint to prevent one person from voting on the same Article tag or experiment tag multiple times
        - Note that for this to work: if type == True, experiment_id must be NULL

"""


class Votes_updated(BaseModel):
    username = peewee.ForeignKeyField(
        User,
        to_field='username'
    )
    # An experiment vote on a key is uniqely identified by a name and
    # experimentID
    name = peewee.CharField(null=True)
    experiment_id = peewee.IntegerField(null=True, db_column='experimentID')
    # An article vote on a key is uniqely identified by a name and article_id
    article_id = peewee.IntegerField(db_column='articleID')  # Refernces PMID

    # A boolean value represents up or down: True = Upvote, False = Downvote
    vote = peewee.BooleanField(null=True)
    # Type specifies what the vote actually indicates -> Experiment / Article
    # True implies Article, False implies Experiment (For space considerations)
    type = peewee.BooleanField()

    class Meta:
        db_table = 'votes'
        constraints = [
            SQL("UNIQUE('name','experiment_id','article_id','userid'")]
        primary_key = False


"""  End Article Table Update  """


class User(BaseModel):
    userid = peewee.PrimaryKeyField()
    password = CharField(null=True)
    emailaddress = CharField(null=True)
    username = CharField(null=True,unique=True)
    collections = CharField(null=True)

    class Meta:
        db_table = 'users'


""" Basically Obsolete Tables at this point """


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


class Concepts(BaseModel):
    name = CharField(db_column='Name', null=True)
    definition = CharField(null=True)
    metadata = CharField(null=True)
    ontology = CharField(null=True)
    uniqueid = peewee.PrimaryKeyField()

    class Meta:
        db_table = 'concepts'
