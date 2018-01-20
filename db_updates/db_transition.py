import sys
sys.path.append("../brainspell")
import models
import updated_models
import json
from peewee import *


def article_transition():
    q = models.Articles.select().execute()  # load entire DB into memory
    for article in q:
        try:
            space, subjects = get_mesh_tags(article.pmid,article.metadata)
            updated_models.Articles_updated.create(
                uniqueid=article.uniqueid,
                timestamp=article.timestamp,
                authors=article.authors,
                title=article.title,
                abstract=article.abstract,
                reference=article.reference,
                pmid=article.pmid,
                doi=article.doi,
                neurosynthid=article.neurosynthid
            )
            add_remaining(article.pmid, article.experiments, space, subjects)
        except:
            return "Execution broke on article uniqueid {0}".format(
                article.uniqueid)


def get_mesh_tags(pmid,metadata_string):
    metadata = json.loads(metadata_string)
    if metadata.get("space"):
        space = metadata['space']
    else:
        space = None
    if metadata.get('nsubjects') and len(metadata.get('nsubjects')) > 0:
        subjects = int(metadata['nsubjects'][0])
    else:
        subjects = None
    output = []
    if metadata.get("meshHeadings"):
        for concept in metadata["meshHeadings"]:
            val = {}
            val["name"] = concept['name']
            if "agree" in concept:
                val['agree'] = concept['agree']
                val['disagree'] = concept['disagree']
            else:
                val['agree'] = 0
                val['disagree'] = 0
            output.append(val)
    # Generate Tags_updated table
    for vote_field in output:
        Tags.insert(
            tag_name = vote_field['name'],
            agree = vote_field['agree'],
            disagree = vote_field['disagree'],
            article_id = pmid
        ).execute()

    return (space, subjects)


def add_remaining(article_reference, experiments_string, space, num_subjects):
    if not experiments_string:
        return
    experiments = json.loads(experiments_string)
    for experiment in experiments:
        if experiment:
            q = updated_models.Experiments_updated.select(
                fn.Max(updated_models.Experiments_updated.experiment_id)).execute()
            if q.count == 0:
                prev_max = -1
            else:
                prev_max = next(q).experiment_id
            updated_models.Experiments_updated.create(
                experiment_id=prev_max + 1,
                title=experiment.get('title'),
                caption=experiment.get('caption'),
                flagged=calc_maximum(experiment.get('markBadTable')),
                num_subjects=num_subjects,
                space=space,
                article_id=article_reference,

            )
            update_experiment_mesh_tags(experiment['tags'],prev_max + 1,article_reference)
            # Prev_max + 1 acts as experiment reference for foreign keys
            add_locations(prev_max + 1, experiment['locations'])

def calc_maximum(dict):
    if not dict:
        return False
    if dict["bad"] > dict["ok"]:
        return True
    else:
        return False


def update_experiment_mesh_tags(tags,experiment_reference,article_ref):
    if not tags:
        return
    output = []
    for tag in tags:
        vals = {}
        if not tag.get("name"):
            pass
        else:
            vals['name'] = tag.get("name")
            if 'agree' in tag:
                vals['agree'] = tag['agree']
                vals['disagree'] = tag['disagree']
            else:
                vals['agree'] = 0
                vals['disagree'] = 0
            output.append(tag)
    for value_dict in output:
        Tags.insert(
            tag_name = value_dict['name'],
            agree = value_dict['agree'],
            disagree = value_dict['disagree'],
            article_id = article_ref,
            experiment_id = experiment_reference
        ).execute()


def add_locations(experiment_reference, locations_array):
    if not locations_array:
        return
    else:
        for location in locations_array:
            if location:
                values = location.split(",")
                if len(values) == 3:
                    x, y, z = [int(x) for x in values]
                    updated_models.Locations_updated.create(
                        x=x,
                        y=y,
                        z=z,
                        experiment_id=experiment_reference
                    )
                elif len(values) == 4:
                    x, y, z, z_score = [int(x) for x in values]
                    updated_models.Locations_updated.create(
                        x=x,
                        y=y,
                        z=z,
                        z_score=z_score,
                        experiment_id=experiment_reference
                    )
                else:
                    print(
                        "Error inserting location {0} for Experiment {1}".format(
                            locations_array, experiment_reference))


"""
Experiment_string Example
[
    {
        "title":" Brain regions showing activation in a main effect of deception",
        "caption":"",
        "locations":["-26,54,14","52,18,12","10,16,32","10,56,24"],
        "markBadTable":{"bad":1,"ok":1},
        "id":90000,
        "tags":[
            {
                "name":"Executive Function",
                "ontology":"cognitive",
                "agree":1,
                "disagree":0
            },
            {
                "name":"Deception",
                "ontology":"cognitive",
                "agree":1,
                "disagree":0
            },
            {
                "name":"Cognition:Social Cognition",
                "ontology":"behavioural",
                "agree":1,
                "disagree":0
            },
            {
                "name":"Deception task",
                "ontology":"tasks",
                "agree":1,
                "disagree":0
            }
        ],
    }
]

"""
