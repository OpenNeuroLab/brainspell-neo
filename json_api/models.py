import peewee
import psycopg2
from playhouse import signals
import time
import peewee
import os
from urllib.parse import urlparse

from peewee import DateTimeField, CharField, IntegerField
"""The following command executed in database_dumps will generate an ORM
python3 -m pwiz --engine=postgresql brainspell_2016-11-01.pgsql > trial.py
"""
# urlparse.uses_netloc.append("postgres")
url = urlparse(os.environ["DATABASE_URL"])

config = dict(
    database = url.path[1:],
    user = url.username,
    password = url.password,
    host= url.hostname,
    port= url.port,
    sslmode = 'require'
)
print(config)

conn = peewee.PostgresqlDatabase(autocommit= True, autorollback = True, **config)
print(conn)


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
    experiments = CharField(null=True)
    metadata = CharField(null=True)
    neurosynthid = CharField(null=True)
    pmid = CharField(null=True)
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

def create_tables(retry=5):
    for i in range(1, retry + 1):
        try:
            conn.create_tables([Articles,Concepts,Log,User], safe=True)
            return
        except Exception as e:
            if (i == retry):
                raise e
            else:
                print('Could not connect to database...sleeping 5')
                time.sleep(5)




