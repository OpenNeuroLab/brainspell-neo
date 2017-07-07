# functions related to search

import re
from functools import reduce

from models import *


def random_search():
    """ Return five random articles from our database. """
    search = Articles.select(
        Articles.pmid,
        Articles.title,
        Articles.authors).order_by(
        fn.Random()).limit(5)
    return search.execute()


# helper function for search queries, generates match objects of target
# columns for search if user specified
def parse_helper(query):
    """
    Return a list of relevant columns user wishes to search
    Follows the PubMed labeling system:
    [au] indicates author
    [ALL] all fields
    [MH] Mesh terms: To be added
    [PMID]: Pubmed ID
    [TIAB]: Title/Abstract
    """

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
                        Articles.reference, Articles.title])
    if mesh.search(query):
        columns.append(Articles.metadata)
    if pmid.search(query):
        columns.append(Articles.pmid)
    if tiab.search(query):
        columns.extend([Articles.title, Articles.abstract])
    formatted_query = re.sub('\[.*\]', '', query).strip().replace(" ", "%")
    if not columns:
        return (None, None, formatted_query)
    matches = [Match(col, formatted_query) for col in columns]
    term = reduce(lambda x, y: x | y, matches)
    return (columns, term, formatted_query)


# param specifies dropdown value from search bar; experiments specifies
# whether to only return the experiments
def formatted_search(query, start, param=None, experiments=False):
    """
    Return either the results of a search, or the experiments that
    correspond to the articles. (based on the "experiments" flag)
    """

    columns, term, formatted_query = parse_helper(query)
    query = formatted_query
    if columns:
        search = Articles.select(
            Articles.pmid,
            Articles.title,
            Articles.authors).where(term).limit(10).offset(start)
        return search.execute()
    else:
        match = Match(
            Articles.title,
            query) | Match(
            Articles.authors,
            query) | Match(
            Articles.abstract,
            query)
        if param == "x":
            match = Match(Articles.experiments, query)
        if param == "p":
            match = Match(Articles.pmid, query)
        if param == "r":
            match = Match(Articles.reference, query)
        # return (search.count(), search.limit(10).offset(start).execute()) #
        # give the total number of results, and output ten results, offset by
        # "start"
        fields = (Articles.pmid, Articles.title, Articles.authors)
        numberResults = 10
        if experiments:
            fields = (Articles.experiments,)
            numberResults = 200
        # search.count() makes the above line slow; TODO: find a better way of
        # doing this
        return Articles.select(
            *fields).where(match).limit(numberResults).offset(start).execute()


def generate_circle(coordinate):  # Coordinate of form "-26,54,14"
    """ Specify a range around a given coordinate to search the database. """

    ordered = [int(x) for x in coordinate.split(",")][0:3]  # Ignore z-score
    search_terms = []
    for i in range(len(ordered)):
        for j in range(-1, 2, 1):
            val = list(ordered)
            val[i] = val[i] + j
            search_terms.append(",".join([str(x) for x in val]))
    return search_terms


def coactivation(coordinate):  # yields around 11,000 coordinates
    """
    Find coordinates associated with a range around a given coordinate.
    """

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
