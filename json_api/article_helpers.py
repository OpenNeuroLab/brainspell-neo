# functions related to adding and editing article data

import re
import urllib.request

import Bio
from Bio import Entrez, Medline
from Bio.Entrez import efetch, esearch, parse, read

from models import *

Entrez.email = "neel@berkeley.edu"

# BEGIN: article helper functions


def update_authors(pmid, authors):
    """ Update the authors for an article. """

    Articles.update(authors=authors).where(Articles.pmid == pmid).execute()


def toggle_vote(pmid, topic, username, direction):
    """ Toggle a user's vote on an article tag. """

    fullArticle = next(
        Articles.select(
            Articles.metadata).where(
            Articles.pmid == pmid).execute())

    target = eval(fullArticle.metadata)['meshHeadings']
    entry = -1

    for i in range(len(target)):
        if target[i]['name'] == topic:
            entry = i
            break

    if entry == -1:  # if the tag hasn't been added yet, then add it
        target.append({
            "name": topic,
            "majorTopic": "N"
        })
        entry = len(target) - 1

    # if no one has voted, then add voting structures
    if "vote" not in target[entry]:
        target[entry]["vote"] = {}
        target[entry]["vote"]["up"] = []
        target[entry]["vote"]["down"] = []

    # toggle the vote
    toggled = False
    for v in range(len(target[entry]["vote"][direction])):
        if target[entry]["vote"][direction][v]["username"] == username:
            del target[entry]["vote"][direction][v]
            toggled = True
    if not toggled:
        target[entry]["vote"][direction].append({
            "username": username  # leave open for any other metadata we may eventually want to include
        })

    # delete any votes in the opposite direction
    otherDirectionLst = ["up", "down"]
    otherDirection = otherDirectionLst[-1 *
                                       otherDirectionLst.index(direction) + 1]
    for v in range(len(target[entry]["vote"][otherDirection])):
        if target[entry]["vote"][otherDirection][v]["username"] == username:
            del target[entry]["vote"][otherDirection][v]

    updatedMetadata = {
        "meshHeadings": target
    }

    # print(updatedMetadata)

    query = Articles.update(
        metadata=updatedMetadata).where(
        Articles.pmid == pmid)
    query.execute()


def add_user_tag(user_tag, id):
    """ Add a custom user tag to the database. """

    main_target = next(
        Articles.select(
            Articles.metadata).where(
            Articles.pmid == id).execute())
    target = eval(main_target.metadata)
    if target.get("user"):
        target["user"].append(user_tag)
    else:
        target["user"] = [user_tag]
    query = Articles.update(metadata=target).where(Articles.pmid == id)
    query.execute()


def get_number_of_articles():
    """ Get the total number of articles in the database. """

    return Articles.select().wrapped_count()

# BEGIN: add article functions


def add_pmid_article_to_database(article_id):
    """
    Given a PMID, use external APIs to get the necessary article data
    in order to add the article to our database.
    """

    pmid = str(article_id)
    handle = efetch("pubmed", id=[pmid], rettype="medline", retmode="text")
    records = list(Medline.parse(handle))
    records = records[0]
    article_info = {}
    article_info["title"] = records.get("TI")
    article_info["PMID"] = pmid
    article_info["authors"] = ', '.join(records.get("AU"))
    article_info["abstract"] = records.get("AB")
    article_info["DOI"] = getDOI(records.get("AID"))
    article_info["experiments"] = ""
    article["metadata"] = str({"meshHeadings": []})
    article["reference"] = None
    identity = ""
    try:
        article_info["experiments"] = {
            "locations": eval(
                urllib.request.urlopen(
                    "http://neurosynth.org/api/studies/peaks/" +
                    str(pmid) +
                    "/").read().decode())["data"]}
        k = article_info["experiments"]["locations"]
        for i in range(len(k)):
            if len(k[i]) == 4:
                identity = k[0]
                k[i] = k[i][1:]
            k[i] = ",".join([str(x) for x in (k[i])])
    except BaseException:
        pass
    article_info["id"] = identity
    article_info["experiments"] = [article_info["experiments"]]
    Articles.create(abstract=article_info["abstract"],
                    authors=article_info["authors"],
                    doi=article_info["DOI"],
                    experiments=article_info["experiments"],
                    pmid=article_info["PMID"],
                    title=article_info["title"])
    return article_info


def getDOI(lst):
    """ Extract the DOI from a Bio.Medline result """

    pattern = r"([0-9]{2}\.[0-9]*\/[a-z]*\.[0-9]*\.[0-9]*)[ ]\[doi\]"
    for item in lst:
        if re.match(pattern, item):
            x = re.match(pattern, item)
            return x.group(1)


def clean_bulk_add(contents):
    """
    A helper function for adding many articles at a time (by uploading a
    JSON file of article information). Clean the data, ensure that only
    complete entries are included, and add all of the entries to our database.
    """

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
                article["metadata"] = str(
                    {"meshHeadings": article["meshHeadings"]})
                del article["meshHeadings"]
            else:
                article["metadata"] = str({"meshHeadings": []})
            if "journal" in article and "year" in article:
                article["reference"] = article["authors"] + \
                    "(" + str(article["year"]) + ") " + article["journal"]
                del article["journal"]
                del article["year"]
            else:
                article["reference"] = None
            # once the article data is clean, add it to a separate list that
            # we'll pass to PeeWee
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
        except BaseException:
            pass
    return clean_articles


def add_bulk(papers, limit=100):  # papers is the entire formatted data set
    """ Add a list of article entries to our database. """

    with conn.atomic():
        for article in range(0, len(papers), limit):  # Inserts limit at a time
            Articles.insert_many(papers[article:article + limit]).execute()

# BEGIN: table helper functions


def delete_row(pmid, exp, row):
    """ Delete a row of coordinates from an experiment. """

    target = Articles.select(
        Articles.experiments).where(
        Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    elem = experiments[exp]
    locations = elem["locations"]
    locations.pop(row)
    Articles.update(
        experiments=experiments).where(
        Articles.pmid == pmid).execute()


def flag_table(pmid, exp):
    """ Flag a table as inaccurate. """

    target = Articles.select(
        Articles.experiments).where(
        Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    elem = experiments[int(exp)]
    if "flagged" in elem:
        elem["flagged"] = 1 - elem["flagged"]
    else:
        elem["flagged"] = 1
    Articles.update(
        experiments=experiments).where(
        Articles.pmid == pmid).execute()


def split_table(pmid, exp, row):
    """ Split a coordinate table into two. """

    target = Articles.select(
        Articles.experiments).where(
        Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    elem = experiments[exp]
    locations = elem["locations"]
    locations1 = locations[0:row]
    locations2 = locations[row:]
    elem["locations"] = locations1
    highestID = int(max([exp["id"] for exp in experiments])) + 1
    secondTable = {
        "title": "",
        "caption": "",
        "locations": locations2,
        "id": highestID
    }
    experiments.insert(exp + 1, secondTable)
    Articles.update(
        experiments=experiments).where(
        Articles.pmid == pmid).execute()


def add_coordinate(pmid, exp, coords):
    """ Add a coordinate row to the end of a table. """

    target = Articles.select(
        Articles.experiments).where(
        Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    elem = experiments[int(exp)]
    elem["locations"].append(coords)
    Articles.update(
        experiments=experiments).where(
        Articles.pmid == pmid).execute()


def add_table_through_text_box(pmid, values):
    """ Add an experiment table using a CSV-formatted string. """

    target = Articles.select(
        Articles.experiments).where(
        Articles.pmid == pmid).execute()
    target = next(target)
    experiments = eval(target.experiments)
    values = values.replace(" ", "").split("\n")
    secondTable = {"title": "", "caption": "", "locations": values,
                   "id": (max([exp["id"] for exp in experiments]) + 1)}
    experiments.insert(len(experiments), secondTable)
    Articles.update(
        experiments=experiments).where(
        Articles.pmid == pmid).execute()


def update_z_scores(id, values):
    """ Update the z-scores for an experiment table. """

    target = Articles.select(
        Articles.experiments).where(
        Articles.pmid == id).execute()
    target = next(target)
    experiments = eval(target.experiments)
    for key, value in values.items():
        table, row = key.split(',')[0], key.split(',')[1]
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
        query = Articles.update(
            experiments=experiments).where(
            Articles.pmid == id)
        query.execute()


def update_table_vote(tag_name, direction, table_num, pmid, column, username):
    """ Update the vote on an experiment tag for a given user. """

    article_obj = Articles.select(
        Articles.experiments).where(
        Articles.pmid == pmid).execute()
    article_obj = next(article_obj)
    article_obj = eval(article_obj.experiments)

    # get the table object
    table_obj = article_obj[table_num]
    entry = -1
    if not table_obj.get(column):
        table_obj[column] = []

    # get the index for the tag
    for i in range(len(table_obj[column])):
        # some entries might be malformed, so check if "tag" is in the dict
        if "tag" in table_obj[column][i]:
            if table_obj[column][i]["tag"] == tag_name:
                entry = i
                break
    if entry == -1:  # if the tag hasn't been added yet, then add it
        table_obj[column].append({
            "tag": tag_name,
        })
        entry = len(table_obj[column]) - 1

    # if no one has voted, then add voting structures
    if "vote" not in table_obj[column][entry]:
        table_obj[column][entry]["vote"] = {}
        table_obj[column][entry]["vote"]["up"] = []
        table_obj[column][entry]["vote"]["down"] = []

    # toggle the vote
    toggled = False
    for v in range(len(table_obj[column][entry]["vote"][direction])):
        if table_obj[column][entry]["vote"][direction][v]["username"] == username:
            del table_obj[column][entry]["vote"][direction][v]
            toggled = True

    if not toggled:
        table_obj[column][entry]["vote"][direction].append({
            "username": username
        })

    # delete any votes in the opposite direction
    otherDirectionLst = ["up", "down"]
    otherDirection = otherDirectionLst[-1 *
                                       otherDirectionLst.index(direction) + 1]
    for v in range(len(table_obj[column][entry]["vote"][otherDirection])):
        if table_obj[column][entry]["vote"][otherDirection][v]["username"] == username:
            del table_obj[column][entry]["vote"][otherDirection][v]

    article_obj[table_num] = table_obj

    query = Articles.update(
        experiments=article_obj).where(
        Articles.pmid == pmid)
    query.execute()
