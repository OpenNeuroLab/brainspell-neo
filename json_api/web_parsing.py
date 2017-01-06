"""Experiment tables are still required before this becomes
functional"""


"""Add these imports back once experiments tables are added"""
from Bio import Medline
from Bio.Entrez import efetch, read, esearch, parse
import re


def searchAll():
    pmid = ["15728770"]
    handle = efetch("pubmed", id=pmid, rettype="medline", retmode="text")
    records =  list(Medline.parse(handle))
    records =  records[0]
    articleInfo = {}
    articleInfo["title"] = records.get("TI")
    articleInfo["PMID"] = pmid[0]
    articleInfo["authors"] = records.get("AU")
    articleInfo["abstract"] = records.get("AB")
    articleInfo["DOI"] = getDOI(records.get("AID"))


def getDOI(lst):
    pattern = r"([0-9]{2}\.[0-9]*\/[a-z]*\.[0-9]*\.[0-9]*)[ ]\[doi\]"
    for item in lst:
        if re.match(pattern, item):
            x = re.match(pattern, item)
            return x.group(1)

""" Need:
        Authors
        Abtract
        DOI
        Experiments
        Metadata
        NeuroSynthID
        PMID
        Reference
        Title
"""