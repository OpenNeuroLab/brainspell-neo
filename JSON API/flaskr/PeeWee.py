import peewee
import psycopg2
from playhouse import signals
import time

dbname = "Brainspell"
user = "admin"
password = "Secret"
host = "Database host address"
port = "Connection port number"


conn = psycopg2.connect(dbname = dbname, user = user,password = password)

conn.connect()

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
    """ORM Model of the Articles Table"""
    UniqueID = peewee.PrimaryKeyField() #FIXME
    TIMESTAMP = peewee.DateTimeField() #FIXME
    Title = peewee.TextField()
    Authors = peewee.TextField()
    Abstract = peewee.TextField()
    Reference = peewee.TextField()
    PMID = peewee.CharField()
    DOI = peewee.CharField()
    NeuroSynthID = peewee.CharField()
    Experiments = peewee.TextField()
    Metadata = peewee.TextField()

class Concepts(BaseModel):
    """ORM Model of the Concepts Table"""
    UniqueID = peewee.PrimaryKeyField() #FIXME
    Name = peewee.IntegerField() #FIXME
    Ontology = peewee.IntegerField()
    Definition = peewee.IntegerField()
    Metadata = peewee.IntegerField()

class Log(BaseModel):
    UniqueID = peewee.PrimaryKeyField() #FIXME
    TIMESTAMP = peewee.DateTimeField() #FIXME
    UserName = peewee.TextField()
    Experiment = peewee.IntegerField() #FIXME
    PMID = peewee.CharField()
    Type = peewee.CharField() #FIXME This is a character set
    Data = peewee.CharField() #FIXME This is a character set
class Users(BaseModel):
    UserID = peewee.PrimaryKeyField()
    Username = peewee.CharField()
    Password = peewee.CharField()
    EmailAddress = peewee.CharField()

def create_tables(retry=5):
    for i in range(1, retry + 1):
        try:
            conn.create_tables([Articles,Concepts,Log,Users], safe=True)
            return
        except Exception as e:
            if (i == retry):
                raise e
            else:
                print('Could not connect to database...sleeping 5')
                time.sleep(5)




