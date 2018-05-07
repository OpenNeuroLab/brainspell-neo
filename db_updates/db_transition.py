import sys
sys.path.append("../brainspell")
import models
import updated_models
import json
from peewee import *
import psycopg2


def article_transition(start = None):
    q = models.Articles.select().execute()  # load entire DB into memory
    q = list(q)
    if start: # Used in case of errors along the way
        saved_index = 0
        while q[saved_index].pmid != start:
            saved_index += 1
        q = q[saved_index:]

    for article in q:
        # try:
        try:
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
            print("CREATED ENTRY {0}".format(article.pmid))
            space, subjects = get_mesh_tags(article.pmid, article.metadata)
            add_remaining(article.pmid, article.experiments, space, subjects)
        except:
            print("Duplicate Detected in Entries")
            pass
        # except:
        #     print("I failed on {0}".format(article.uniqueid))
        #     return "Execution broke on article uniqueid {0}".format(
        #         article.uniqueid)


def get_mesh_tags(pmid, metadata_string):
    if not metadata_string:
        return
    try:
        metadata = json.loads(metadata_string)
    except: # Weirdly formatted CDATA Fields
        metadata_string = metadata_string.replace("'","\"")    
        metadata_string = metadata_string.replace("\n","") # newline characters sometimes exist in structure and need to be removed
        metadata = json.loads(
            metadata_string.replace("<!","").replace("CDATA","").replace(">","")
        )


    while (type(metadata) == list):
        print("Metadata for {0} had length {1} and I used the elements in 1".format(pmid,len(metadata)))
        metadata = metadata[0] # Unnecessarily nested structures

    if metadata.get("space"):
        space = metadata['space']
    else:
        space = None
    if metadata.get('nsubjects') and len(metadata.get('nsubjects')) > 0:
        try:
            subjects = int(metadata['nsubjects'][0])
        except:
            # Handles the case of literals like '10+15' somehow being here
            try:
                print("Literal attempting to Evaluate {0}".format(metadata['nsubjects'][0]))
                subjects = eval(metadata['nsubjects'][0])
            except:
                subjects = None

    else:
        subjects = None
    output = []
    if metadata.get("meshHeadings"):
        for concept in metadata["meshHeadings"]:
            val = {}
            try:
                val["name"] = concept['name']
                if "agree" in concept:
                    val['agree'] = concept['agree']
                    val['disagree'] = concept['disagree']
                else:
                    val['agree'] = 0
                    val['disagree'] = 0
                output.append(val)
            except:
                pass 
                # There are certain articles with 
                # Extremely malformatted voting systems 
                # Potentially due to changes in our internal representation. Since these are entirely test votes, I am ommitting these 
                # These changes begin with PMID: 17449179
    # Generate Tags_updated table
    for vote_field in output:
        try:
            updated_models.Tags_updated.insert(
                tag_name=vote_field['name'],
                agree=vote_field['agree'],
                disagree=vote_field['disagree'],
                article_id=str(pmid)
            ).execute()
        except:
            print("Duplicate Tag {0} Found for Article {1}".format(vote_field['name'],pmid))
            pass

    return (space, subjects)


def add_remaining(article_reference, experiments_string, space, num_subjects):
    if not experiments_string:
        return
    try:
        experiments = json.loads(experiments_string)
    except:
        experiments_string = experiments_string.replace("'","\"") 
        experiments = json.loads(experiments_string)
    if not experiments:
        return # Handles experiments = 'null' case
    for experiment in experiments:
        if experiment:
            q = updated_models.Experiments_updated.select(
                fn.Max(updated_models.Experiments_updated.experiment_id)).execute()
            if q.count == 0:
                prev_max = -1
            else:
                prev_max = list(q)[0].experiment_id
                if not prev_max:
                    prev_max = 0
            updated_models.Experiments_updated.create(
                experiment_id=prev_max + 1,
                title=experiment.get('title'),
                caption=experiment.get('caption'),
                flagged=calc_maximum(experiment.get('markBadTable')),
                num_subjects=num_subjects,
                space=space,
                article_id=article_reference,

            )
            update_experiment_mesh_tags(
                experiment.get('tags'), prev_max + 1, article_reference)
            # Prev_max + 1 acts as experiment reference for foreign keys
            add_locations(prev_max + 1, experiment.get('locations'))


def calc_maximum(dict):
    if not dict:
        return False
    if dict["bad"] > dict["ok"]:
        return True
    else:
        return False


def update_experiment_mesh_tags(tags, experiment_reference, article_ref):
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
        try:
            updated_models.Tags_updated.insert(
                tag_name=value_dict['name'],
                agree=value_dict['agree'],
                disagree=value_dict['disagree'],
                article_id=article_ref,
                experiment_id=experiment_reference
            ).execute()
        except:
            print("Duplicate found for tag {0} in article {1} and experiment {2}".
                  format(value_dict['name'],article_ref,experiment_reference))
            pass


def add_locations(experiment_reference, locations_array):
    if not locations_array:
        return
    else:
        for location in locations_array:
            if location:
                values = location.split(",")
                if len(values) == 3:
                    try:
                        x, y, z = [int(x) for x in values]
                        updated_models.Locations_updated.create(
                            x=x,
                            y=y,
                            z=z,
                            experiment_id=experiment_reference
                        )
                    except:
                        print("Duplicate found for location {0}".format(location))
                        pass
                elif len(values) == 4:
                    try:
                        x, y, z, z_score = [int(x) for x in values]
                        updated_models.Locations_updated.create(
                            x=x,
                            y=y,
                            z=z,
                            z_score=z_score,
                            experiment_id=experiment_reference
                        )
                    except:
                        print("Duplicate Found for Location {0}".format(location))
                        pass

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
if __name__ == "__main__":
    article_transition('20884359')




