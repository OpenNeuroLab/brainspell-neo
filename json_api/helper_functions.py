import Bio
from Bio import Medline
from Bio import Entrez
from Bio.Entrez import efetch, read, esearch, parse
import re
import urllib.request

Entrez.email = "neel@berkeley.edu"

# getArticleData(20060480)

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
    articleInfo["coordinates"] = ""
    try:
        urllib.request.urlopen("http://neurosynth.org/api/studies/peaks/" + pmid + "/").read()
    except:
        pass
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