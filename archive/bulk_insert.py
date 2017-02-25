""" 
Assumes the data is of the following form: 
	papers = [
		{"timestamp": "___",
		"abstract": "___",
		"authors": "___",
		"doi": "___",
		"experiments": "___",
		"metadata": "___",
		"neurosynth": "___",
		"pmid": "___",
		"reference": "___",
		"title": "___",
		},
		{...}
		.
		.
		.

	]
"""
from peewee import * 

# Checks for existing PMID--> Very slow 
def check(pmid):
	existing = Articles.select().where(Article.pmid == pmid)
	if existing.execute().count == 0:
		return False 
	else:
		return True 



def addall(papers, limit=100): # Papers is the entire formatted data set
	with db.atomic():
		for article in range(0,len(papers), limit): # Inserts limit at a time
			Articles.insert_many(papers[article:article+limit]).execute()












