from urllib.parse import urlparse
import peewee
from playhouse import signals
from playhouse.postgres_ext import *
from playhouse.csv_loader import *




print("USING DOCKER")
config = dict(
    database="docker",
    user="docker",
    password='docker',
    host="localhost",
    port=5433,

)

conn = PostgresqlExtDatabase(
    autocommit=True,
    autorollback=True,
    register_hstore=False,
    **config
)


"""Initialize Articles table"""
fields = [IntegerField(),DateTimeField(null=True),TextField(null=True),TextField(null=True),TextField(null=True),
          TextField(null=True),TextField(null=True),TextField(null=True),TextField(null=True),TextField(null=True),TextField(null=True)]
field_names = ['uniqueid','timestamp','abstract','authors','doi','experiments','metadata','neurosynthid','pmid','reference','title']

Articles = load_csv(conn,'../data/articles_2016_07-23.csv',fields=fields,field_names=field_names)


"""Initialize User table """
fields = [TextField(null=True),TextField(null=True),TextField(null=True),TextField(null=True),TextField(null=True)]
field_names = ["password","emailaddress","userid","username","collections"]

User = load_csv(conn, '../data/user_data.csv',fields=fields,field_names=field_names)


"""Leave remaining fields uninitialized for the time being"""
class User_metadata():
    pass

class Log():
    pass

class Concepts():
    pass

