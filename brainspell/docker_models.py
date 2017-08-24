import os
import time
from urllib.parse import urlparse

import peewee
import playhouse
import psycopg2
from peewee import CharField, DateTimeField, IntegerField
from playhouse import signals
from playhouse.postgres_ext import *
from playhouse.csv_loader import *



config = dict(
    database="docker",
    user="docker",
    password='docker',
    host="0.0.0.0",
    port=5433,

)

conn = PostgresqlExtDatabase(
    autocommit=True,
    autorollback=True,
    register_hstore=False,
    **config
)


load_csv(conn,'../docker/postgres/data/articles_2016_07-23.csv')

