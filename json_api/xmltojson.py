from peewee import * 

import xml.etree.ElementTree as ET
tree = ET.parse('brainspell2.xml')
root = tree.getroot()

from models import * 

def convertToJSON(xmlObj):
    p = {}
    for attr in xmlObj:
        if len(attr) != 0:
            if attr.tag.lower() in p:
                if not isinstance(p[attr.tag.lower()], list):
                    value = p[attr.tag.lower()]
                    p[attr.tag.lower()] = [value]
                p[attr.tag.lower()].append(convertToJSON(attr))
            else:
                p[attr.tag.lower()] = convertToJSON(attr)
        else:
            if attr.text is not None:
                attr.text = attr.text.replace("\n", "").replace("\t", "")
            if attr.tag.lower() in p:
                if not isinstance(p[attr.tag.lower()], list):
                    value = p[attr.tag.lower()]
                    p[attr.tag.lower()] = [value]
                p[attr.tag.lower()].append(attr.text)
            else:
                p[attr.tag.lower()] = attr.text
    return p

dictionary = convertToJSON(root)

for p in dictionary["paper"]:
    try:
        # title and pmid are done

        p["metadata"] = p["pubmed"]
        del p["pubmed"]
        # abstract
        p["abstract"] = p["metadata"]["abstract"]
        del p["metadata"]["abstract"]
        # metadata
        del p["metadata"]["source"]
        p["metadata"]["meshHeadings"] = p["metadata"]["meshcodes"]["tag"]
        del p["metadata"]["meshcodes"]
        if type(p["metadata"]["meshHeadings"]) != list:
            p["metadata"]["meshHeadings"] = [p["metadata"]["meshHeadings"]]
        p["metadata"] = str(p["metadata"])
        # timestamp and doi
        p["neurosynth"] = p["pmid"]
        p["timestamp"] = ""
        if "doi" in p:
            if p["doi"] is None:
                p["doi"] = ""
        # experiments
        if type(p["experiment"]) != list:
            p["experiment"] = [p["experiment"]]
        p["experiments"] = str(p["experiment"])
        del p["experiment"]
        # authors
        authorStr = p["authors"]["author"]
        if type(authorStr) == str:
            p["authors"] = authorStr
        else:
            p["authors"] = ",".join(authorStr)
        # reference
        p["reference"] = p["authors"] + "(" + p["year"] + ") " + p["journal"]
        del p["year"]
        del p["journal"]
    except:
        pass

def add_bulk(papers, limit=100): # Papers is the entire formatted data set
    with conn.atomic():
        for article in range(0,len(papers), limit): # Inserts limit at a time
            Articles.insert_many(papers[article:article+limit]).execute()

papers = dictionary["paper"]




