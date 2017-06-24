# functions related to adding and editing article data

from models import *
import Bio
from Bio import Medline
from Bio import Entrez
from Bio.Entrez import efetch, read, esearch, parse
import re
import urllib.request

Entrez.email = "neel@berkeley.edu"

# BEGIN: article helper functions

# updates the authors for an article
def update_authors(pmid, authors):
    Articles.update(authors = authors).where(Articles.pmid == pmid).execute()

# toggles a vote on an article tag
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


# Adds a custom user tag to the Database
def add_user_tag(user_tag,id):
    main_target = next(Articles.select(Articles.metadata).where(Articles.pmid == id).execute())
    target = eval(main_target.metadata)
    if target.get("user"):
        target["user"].append(user_tag)
    else:
        target["user"] = [user_tag]
    query = Articles.update(metadata = target).where(Articles.pmid == id)
    query.execute()

# BEGIN: add article functions

def getArticleData(article_id):
    # TODO: add empty metadata field, add reference
    pmid = str(article_id)
    handle = efetch("pubmed", id=[pmid], rettype="medline", retmode="text")
    records =  list(Medline.parse(handle))
    records =  records[0]
    articleInfo = {}
    articleInfo["title"] = records.get("TI")
    articleInfo["PMID"] = pmid
    articleInfo["authors"] = records.get("AU")
    articleInfo["abstract"] = records.get("AB")
    articleInfo["DOI"] = getDOI(records.get("AID"))
    articleInfo["experiments"] = ""
    identity = "" 
    try:
        articleInfo["experiments"] = {"locations": eval(urllib.request.urlopen("http://neurosynth.org/api/studies/peaks/" + str(pmid) + "/").read().decode())["data"]}
        k = articleInfo["experiments"]["locations"]
        for i in range(len(k)):
            print("KI is ",k[i])
            if len(k[i]) == 4:
                identity = k[0]
                k[i] = k[i][1:]
            k[i] = ",".join([str(x) for x in (k[i])])
    except:
        pass
    articleInfo["id"] = identity
    return articleInfo

def getDOI(lst):
    pattern = r"([0-9]{2}\.[0-9]*\/[a-z]*\.[0-9]*\.[0-9]*)[ ]\[doi\]"
    for item in lst:
        if re.match(pattern, item):
            x = re.match(pattern, item)
            return x.group(1)

def clean_bulk_add(contents):
    clean_articles = []
    for article in contents:
        try:
            if "timestamp" not in article:
                article["timestamp"] = None
            article["authors"] = ",".join(article["authors"])
            if "doi" not in article:
                article["doi"] = None
            if "experiments" in article:
                article["experiments"] = str(article["experiments"])
            else:
                article["experiments"] = str([])
            if "meshHeadings" in article:
                article["metadata"] = str({"meshHeadings": article["meshHeadings"]})
                del article["meshHeadings"]
            else:
                article["metadata"] = str({"meshHeadings": []})
            if "journal" in article and "year" in article:
                article["reference"] = article["authors"] + "(" + str(article["year"]) + ") " + article["journal"]
                del article["journal"]
                del article["year"]
            else:
                article["reference"] = None
            # once the article data is clean, add it to a separate list that we'll pass to PeeWee
            article = {
                "timestamp": article["timestamp"],
                "abstract": article["abstract"],
                "authors": article["authors"],
                "doi": article["doi"],
                "experiments": article["experiments"],
                "metadata": article["metadata"],
                "neurosynthid": None,
                "pmid": article["pmid"],
                "reference": article["reference"],
                "title": article["title"]
            }
            clean_articles.append(article)
        except:
            pass
    return clean_articles

def add_bulk(papers, limit=100): # Papers is the entire formatted data set
    with conn.atomic():
        for article in range(0,len(papers), limit): # Inserts limit at a time
            Articles.insert_many(papers[article:article+limit]).execute()

# BEGIN: table helper functions

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
    highestID = int(max([exp["id"] for exp in experiments])) + 1
    secondTable = {
        "title": "", 
        "caption": "", 
        "locations": locations2, 
        "id": highestID
    }
    experiments.insert(int(exp) + 1, secondTable)
    Articles.update(experiments = experiments).where(Articles.pmid == pmid).execute()

def add_coordinate(pmid, exp, coords): # adds a coordinate row to the end of a table
    target = Articles.select(Articles.experiments).where(Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    elem = experiments[int(exp)]
    elem["locations"].append(coords)
    Articles.update(experiments = experiments).where(Articles.pmid == pmid).execute()

def add_table_through_text_box(pmid, values):
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

def update_table_vote(tagName,direction,table_num,pmid,column,email): # TODO: needs to be commented more thoroughly
    table_num = eval(table_num)
    target = Articles.select(Articles.experiments).where(Articles.pmid == pmid).execute()
    target = next(target)
    target = eval(target.experiments)
    email = email.decode()

    # get the table object
    tableObj = target[table_num]
    entry = -1
    if not tableObj.get(column):
        tableObj[column] = []
    for i in range(len(tableObj[column])):
        if tableObj[column][i]["element"] == tagName:
            entry = i
            break
    if entry == -1: # if the tag hasn't been added yet, then add it
        tableObj[column].append({
            "element": tagName,
        })
        entry = len(tableObj[column]) - 1

    if "vote" not in tableObj[column][entry]: # if no one has voted, then add voting structures
        tableObj[column][entry]["vote"] = {}
        tableObj[column][entry]["vote"]["up"] = []
        tableObj[column][entry]["vote"]["down"] = []

    tableObj[column][entry]["vote"][direction].append(email)

    target[table_num] = tableObj

    query = Articles.update(experiments = target).where(Articles.pmid == pmid)
    query.execute()
