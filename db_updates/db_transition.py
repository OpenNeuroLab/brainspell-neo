import sys
sys.path.append("../brainspell")
import models
import updated_models
import json


def article_transition():
    q = models.Articles.select().execute()
    for article in q:
        updated_models.Articles_updated.create(
            uniqueid=article.uniqueid,
            timestamp=article.timestamp,
            authors=article.authors,
            title=article.title,
            abstract=article.abstract,
            reference=article.reference,
            pmid=article.pmid,
            doi=article.doi,
            neurosynthid=article.neurosynthid,
            metadata=article.metadata
        )
        add_remaining(article.pmid, article.experiments)


def add_remaining(article_reference, experiments_string):
    if not experiments_string:
        return
    experiments = json.loads(experiments_string)
    for experiment in experiments:
        if experiment:
            q = updated_models.Experiments_updated.select(
                fn.Max(updated_models.Experiments_updated.experiment_id))
            prev_max = next(q.execute())
            prev_max = prev_max.experiment_id
            updated_models.Experiments_updated.create(
                experiment_id=prev_max + 1,
                title=experiment['title'],
                caption=experiment['caption'],
                # TODO: This field is still a JSON string
                mark_bad_table=json.dumps(experiment['markBadTable']),
                article_id=article_reference
            )
            # Prev_max + 1 acts as experiment reference for foreign keys
            add_tags(prev_max + 1, experiment['tags'])
            add_locations(prev_max + 1, experiment['locations'])


def add_tags(experiment_reference, tags):
    if not tags:
        return
    for tag in tags:
        if tag:
            updated_models.Tags_updated.create(
                name=tag['name'],
                ontology=tag['ontology'],
                agree=tag['agree'],
                disagree=tag['disagree'],
                experiment_id=experiment_reference
            )


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
