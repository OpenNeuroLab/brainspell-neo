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
# urlparse.uses_netloc.append("postgres")
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

#print(config)
#Now using extDatabase for Postgres full text search
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
    [MH] Mesh terms --> To be added
    [PMID] --> Pubmed ID
    [TIAB] --> Title/Abstract
"""

def parse(query): # TODO: needs to be commented
    columns = []
    au = re.compile(r"\[au]")
    all = re.compile(r"\[ALL]")
    mesh = re.compile(r"\[MH]")
    pmid = re.compile(r"\[PMID]")
    tiab = re.compile(r"\[TIAB]")
    if au.search(query):
        columns.append(Articles.authors)
    if all.search(query):
        columns.extend([Articles.abstract,
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
    formatted_query = re.sub('\[.*\]','',query).strip().replace(" ", "%")
    if not columns:
        return (None,None,formatted_query)
    matches = [Match(col,formatted_query) for col in columns]
    term = reduce(lambda x,y:x|y, matches)
    return (columns,term,formatted_query)

# used by the search page; an overloaded function that returns either the results of a search, or the experiments that correspond to the articles
def formatted_search(query, start, param=None, experiments=False): # param specifies dropdown value from search bar; experiments specifies whether to only return the experiments
    columns, term, formatted_query = parse(query)
    query = formatted_query
    print(query) 
    if columns:
        search = Articles.select(Articles.pmid, Articles.title, Articles.authors).where(term).limit(10).offset(start)
        return search.execute()
    else:
        match = Match(Articles.title, query) | Match(Articles.authors, query) | Match(Articles.abstract, query)
        if param == "x":
            match = Match(Articles.experiments, query)
        if param == "p":
            match = Match(Articles.pmid, query)
        if param == "r":
            match = Match(Articles.reference, query)
        # return (search.count(), search.limit(10).offset(start).execute()) # give the total number of results, and output ten results, offset by "start"
        fields = (Articles.pmid, Articles.title, Articles.authors)
        numberResults = 10
        if experiments:
            fields = (Articles.experiments,)
            numberResults = 200
        return Articles.select(*fields).where(match).limit(numberResults).offset(start).execute() # search.count() makes the above line slow; TODO: find a better way of doing this

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

def get_saved_articles(email):
    return User_metadata.select().where(User_metadata.user_id==email).execute()

def user_login(email, password):
    user = User.select().where((User.emailaddress == email) & (User.password == password))
    return user.execute().count == 1

def valid_api_key(api_key):
    user = User.select().where((User.password == api_key)) # using password hashes as API keys for now; can change later
    return user.execute().count >= 1

def register_user(username,email,password):
    if (User.select().where((User.emailaddress == email)).execute().count == 0):
        hasher=hashlib.sha1()
        hasher.update(password)
        password = hasher.hexdigest()
        User.create(username = username, emailaddress = email, password = password)
        return True
    else:
        return False

def generate_circle(coordinate): #Coordinate of form "-26,54,14"
    ordered = [int(x) for x in coordinate.split(",")][0:3] #Ignore z-score
    search_terms = []
    for i in range(len(ordered)):
        for j in range(-1,2,1):
            val = list(ordered)
            val[i] = val[i] + j
            search_terms.append(",".join([str(x) for x in val]))
    return search_terms

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

def delete_row(pmid, exp, row):
    target = Articles.select(Articles.experiments).where(Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    elem = experiments[int(exp)]
    locations = elem["locations"]
    locations.pop(int(row))
    Articles.update(experiments = experiments).where(Articles.pmid == pmid).execute()

def flag_table(pmid, exp):
    target = Articles.select(Articles.experiments).where(Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    elem = experiments[int(exp)]
    if "flagged" in elem:
        elem["flagged"] = 1 - elem["flagged"]
    else:
        elem["flagged"] = 1
    print(elem["flagged"])
    Articles.update(experiments = experiments).where(Articles.pmid == pmid).execute()

def split_table(pmid, exp, row):
    target = Articles.select(Articles.experiments).where(Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    elem = experiments[int(exp)]
    locations = elem["locations"];
    locations1 = locations[0:int(row)]
    locations2 = locations[int(row):]
    elem["locations"] = locations1
    secondTable = {"title": "", "caption": "", "locations": locations2, "id": (max([exp["id"] for exp in experiments]) + 1)}
    experiments.insert(int(exp) + 1, secondTable)
    Articles.update(experiments = experiments).where(Articles.pmid == pmid).execute()

def add_coordinate(pmid, exp, coords): # adds a coordinate row to the end of a table
    target = Articles.select(Articles.experiments).where(Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    elem = experiments[int(exp)]
    elem["locations"].append(coords)
    Articles.update(experiments = experiments).where(Articles.pmid == pmid).execute()

def update_authors(pmid, authors):
    Articles.update(authors = authors).where(Articles.pmid == pmid).execute()

def add_table_text(pmid, values):
    target = Articles.select(Articles.experiments).where(Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    values = values.replace(" ", "").split("\n")
    secondTable = {"title": "", "caption": "", "locations": values, "id": (max([exp["id"] for exp in experiments]) + 1)}
    experiments.insert(len(experiments), secondTable)
    Articles.update(experiments = experiments).where(Articles.pmid == pmid).execute()


def update_z_scores(id,user,values): #TODO maybe save the user that inserted the data
    target = Articles.select(Articles.experiments).where(Articles.pmid == id).execute()
    target = next(target)
    experiments = eval(target.experiments)
    for key,value in values.items():
        table, row = key.split(',')[0],key.split(',')[1]
        table = eval(table)
        row = eval(row)
        target = 0
        for i in range(len(experiments)):
            if experiments[i].get('id') == table:
                target = i
                break
        position = experiments[target]
        location_set = position['locations'][row]
        location_set = location_set + ',' + str(value)
        experiments[target]['locations'][row] = location_set
        query = Articles.update(experiments=experiments).where(Articles.pmid == id)
        query.execute()

def toggle_vote(pmid, topic, email, direction):
    fullArticle = next(Articles.select(Articles.metadata).where(Articles.pmid == pmid).execute())

    target = eval(fullArticle.metadata)['meshHeadings']
    entry = -1

    for i in range(len(target)):
        if target[i]['name'] == topic:
            entry = i
            break

    if entry == -1: # if the tag hasn't been added yet, then add it
        target.append({
            "name": topic,
            "majorTopic": "N"
        })
        entry = len(target) - 1

    if "vote" not in target[entry]: # if no one has voted, then add voting structures
        target[entry]["vote"] = {}
        target[entry]["vote"]["up"] = []
        target[entry]["vote"]["down"] = []

    # toggle the vote
    toggled = False
    for v in range(len(target[entry]["vote"][direction])):
        if target[entry]["vote"][direction][v]["email"] == email:
            del target[entry]["vote"][direction][v]
            toggled = True
    if not toggled:
        target[entry]["vote"][direction].append({
            "email": email # leave open for any other metadata we may eventually want to include
        })

    # delete any votes in the opposite direction
    otherDirectionLst = ["up", "down"]
    otherDirection = otherDirectionLst[-1 * otherDirectionLst.index(direction) + 1]
    for v in range(len(target[entry]["vote"][otherDirection])):
        if target[entry]["vote"][otherDirection][v]["email"] == email:
            del target[entry]["vote"][otherDirection][v]

    updatedMetadata = {
        "meshHeadings": target
    }

    # print(updatedMetadata)

    query = Articles.update(metadata = updatedMetadata).where(Articles.pmid == pmid)
    query.execute()

def add_user_tag(user_tag,id):
    main_target = next(Articles.select(Articles.metadata).where(Articles.pmid == id).execute())
    target = eval(main_target.metadata)
    if target.get("user"):
        target["user"].append(user_tag)
    else:
        target["user"] = [user_tag]
    query = Articles.update(metadata = target).where(Articles.pmid == id)
    query.execute()

def update_table_vote(element,direction,table_num,pmid,column,email):
    table_num = eval(table_num)
    target = Articles.select(Articles.experiments).where(Articles.pmid == pmid).execute()
    target = next(target)
    target = eval(target.experiments)
    k = target[table_num]
    entry = -1
    if not k.get(column):
        k[column] = []
    for i in range(len(k[column])):
        if k[column][i] == element:
            entry = i
            break

    if entry == -1: # if the tag hasn't been added yet, then add it
        k[column].append({
            "name": element,
            "majorTopic": "N"
        })
        entry = len(target) - 1

    if "vote" not in target[entry]: # if no one has voted, then add voting structures
        target[entry]["vote"] = {}
        target[entry]["vote"]["up"] = []
        target[entry]["vote"]["down"] = []

    # toggle the vote
    toggled = False
    for v in range(len(target[entry]["vote"][direction])):
        if target[entry]["vote"][direction][v]["email"] == email:
            del target[entry]["vote"][direction][v]
            toggled = True
    if not toggled:
        target[entry]["vote"][direction].append({
            "email": email # leave open for any other metadata we may eventually want to include
        })

    # delete any votes in the opposite direction
    otherDirectionLst = ["up", "down"]
    otherDirection = otherDirectionLst[-1 * otherDirectionLst.index(direction) + 1]
    for v in range(len(target[entry]["vote"][otherDirection])):
        if target[entry]["vote"][otherDirection][v]["email"] == email:
            del target[entry]["vote"][otherDirection][v]

    updatedMetadata = {
        "meshHeadings": target
    }

    # print(updatedMetadata)
    target[table_num] = k

    query = Articles.update(experiments = target).where(Articles.pmid == pmid)
    query.execute()



