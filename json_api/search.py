# functions related to search

from models import *

def random_search():
    search = Articles.select(Articles.pmid, Articles.title, Articles.authors).order_by(fn.Random()).limit(5)
    return search.execute()

# helper function for search queries
def parse_helper(query): # TODO: needs to be commented
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
    columns, term, formatted_query = parse_helper(query)
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

def get_article(query):
    search = Articles.select().where(Articles.pmid == query)
    return search.execute()
    