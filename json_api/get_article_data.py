"""Experiment tables are still required before this becomes
functional"""


"""Add these imports back once experiments tables are added"""
import Bio
from Bio import Medline
from Bio import Entrez
from Bio.Entrez import efetch, read, esearch, parse
import re
import urllib.request

Entrez.email = "neel@berkeley.edu"

# getArticleData(20060480)

def getArticleData(article_id):
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
    articleInfo["coordinates"] = urllib.request.urlopen("http://neurosynth.org/api/studies/peaks/" + pmid + "/").read()
    return articleInfo

def getDOI(lst):
    pattern = r"([0-9]{2}\.[0-9]*\/[a-z]*\.[0-9]*\.[0-9]*)[ ]\[doi\]"
    for item in lst:
        if re.match(pattern, item):
            x = re.match(pattern, item)
            return x.group(1)

""" Need:
        Metadata
        NeuroSynthID
        Reference
"""