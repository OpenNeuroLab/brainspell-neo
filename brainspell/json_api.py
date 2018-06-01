# JSON API classes

import brainspell
from article_helpers import *
from base_handler import *
from search_helpers import *
from user_account_helpers import *

# For GitHub OAuth
import requests
import urllib.parse
import os
import hashlib
from tornado.concurrent import run_on_executor

import itertools

REQ_DESC = "The fields to search through. 'x' is experiments, 'p' is PMID, 'r' is reference, and 't' is title + authors + abstract."
START_DESC = "The offset of the articles to show; e.g., start = 10 would return results 11 - 20."
PUT = requests.put
GET = requests.get
POST = requests.post

assert "github_frontend_client_id" in os.environ \
    and "github_frontend_client_secret" in os.environ, \
    "You need to set the 'github_frontend_client_id' and 'github_frontend_client_secret' environment variables."

assert "github_frontend_dev_client_id" in os.environ \
    and "github_frontend_dev_client_secret" in os.environ, \
    "You need to set the 'github_frontend_dev_client_id' and 'github_frontend_dev_client_secret' environment variables."


class ListEndpointsEndpointHandler(BaseHandler):
    """ Return a list of all JSON API endpoints.
    Do not include /help pages, or aliases. """

    parameters = {}

    endpoint_type = Endpoint.PULL_API

    def process(self, response, args):
        endpoints = brainspell.getJSONEndpoints()
        response["endpoints"] = [name for name, cls in endpoints if name[len(
            name) - 1:] != "/" and name[len(name) - 4:] != "help"]
        return response


# BEGIN: Authentication endpoints

class GithubOauthProductionEndpointHandler(BaseHandler):
    """ GitHub login authentication. Return the GitHub token and
    Brainspell API key. """

    parameters = {
        "code": {
            "type": str,
            "description": "The code returned after GitHub OAuth."
        }
    }

    endpoint_type = Endpoint.PULL_API

    client_id_key = "github_frontend_client_id"
    client_secret_key = "github_frontend_client_secret"

    def process(self, response, args):
        code = args["code"]

        data = {
            "client_id": os.environ[self.client_id_key],
            "client_secret": os.environ[self.client_secret_key],
            "code": code
        }

        # TODO: Make asynchronous, since this is blocking.
        result = requests.post(
            "https://github.com:443/login/oauth/access_token",
            data
        )

        params = urllib.parse.parse_qs(result.text)

        try:
            response["github_token"] = params["access_token"][0]
            user = yield self.github_request(GET, "user", params["access_token"][0])
            # idempotent operation to make sure GitHub user is in our
            # database
            register_github_user(user)
            hasher = hashlib.sha1()
            hasher.update(str(user["id"]).encode('utf-8'))
            api_key = hasher.hexdigest()
            response["api_key"] = api_key
        except BaseException:
            response["success"] = 0
            response["description"] = "Authentication failed."

        return response


class GithubOauthDevelopmentEndpointHandler(
        GithubOauthProductionEndpointHandler):
    """ Endpoint for development OAuth. """

    client_id_key = "github_frontend_dev_client_id"
    client_secret_key = "github_frontend_dev_client_secret"


# BEGIN: Collections v2 endpoints

class CreateCollectionEndpointHandler(BaseHandler):
    """ Create a repository and the necessary files for a new collection. """

    parameters = {
        "collection_name": {
            "type": str,
            "description": "The name of this collection, as seen and defined by the user."},
        "description": {
            "type": str},
        "inclusion_criteria": {
            "type": json.loads,
            "description": "A JSON-serialized list of inclusion criteria.",
            "default": "[]"},
        "exclusion_criteria": {
            "type": json.loads,
            "description": "A JSON-serialized list of exclusion criteria.",
            "default": "[]"},
        "tags": {
            "type": json.loads,
            "description": "JSON-serialized list of tags.",
            "default": "[]"},
        "github_token": {
            "type": str}}

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def validate(self, j):
        # Validate a list of strings.
        if not isinstance(j, list):
            return False
        for s in j:
            if not isinstance(s, str):
                return False
        return True

    def process(self, response, args):
        # Validate the JSON arguments.
        v1 = self.validate(args["inclusion_criteria"])
        v2 = self.validate(args["exclusion_criteria"])
        v3 = self.validate(args["tags"])
        if not (v1 and v2 and v3):
            response["success"] = 0
            response["description"] = "One of the JSON inputs was invalid."
            return response

        # Create the repository.

        repo_data = {
            "name": get_repo_name_from_collection(args["collection_name"]),
            "description": args["description"],
        }

        yield self.github_request(
            POST,
            "user/repos",
            args["github_token"],
            repo_data)

        # Create the metadata.json file.

        username = get_github_username_from_api_key(args["key"])

        collection_metadata = {
            "description": args["description"],
            "unmapped_pmids": [],
            "exclusion_criteria": args["exclusion_criteria"],
            "inclusion_criteria": args["inclusion_criteria"],
            "tags": args["tags"],
            "search_to_pmids": {}
        }

        metadata_data = {"message": "Add metadata.json",
                         "content": encode_for_github(collection_metadata)}

        yield self.github_request(PUT,
                                  "repos/{0}/{1}/contents/metadata.json".format(username,
                                                                                get_repo_name_from_collection(args["collection_name"])),
                                  args["github_token"],
                                  metadata_data)

        return response


class GetCollectionInfoEndpointHandler(BaseHandler):
    """ Get the PMIDs and metadata associated with a collection. """

    parameters = {
        "collection_name": {
            "type": str,
            "description": "The name of this collection, as seen and defined by the user."
        },
        "github_token": {
            "type": str
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # Get the metadata file from the GitHub repository for this collection.

        collection_name = get_repo_name_from_collection(
            args['collection_name'])
        user = get_github_username_from_api_key(args['key'])
        collection_values = yield self.github_request(
            GET, "repos/{0}/{1}/contents/metadata.json".format(
                user, collection_name), args["github_token"])

        response["collection_info"] = decode_from_github(
            collection_values["content"])

        return response


class AddToCollectionEndpointHandler(BaseHandler):
    """ Add the given PMIDs to a collection. """

    parameters = {
        "collection_name": {
            "type": str,
            "description": "The name of this collection, as seen and defined by the user."
        },
        "github_token": {
            "type": str
        },
        "search_to_pmids": {
            "type": json.loads,
            "dscription": "A JSON-serialized dictionary mapping search strings to lists of PMIDs. Map[String, List[Integer]]",
            "default": "{}"
        },
        "unmapped_pmids": {
            "type": json.loads,
            "description": "A JSON-serialized list of PMIDs to add to this collection, without specifying a search string.",
            "default": "[]"
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def add_new_pmids(self, search_pmids, unmapped_pmids):
        failures = []
        all_pmids = list(
            itertools.chain(
                *search_pmids.values())) + unmapped_pmids
        for pmid in all_pmids:
            if check_existence(pmid).count == 0:
                if not add_pmid_article_to_database(pmid):
                    failures.append(pmid)
        return failures

    def validate(self, pmids):
        if not isinstance(pmids, list):
            return False
        for p in pmids:
            # Make sure that each PMID is a valid integer.
            try:
                v = int(p)
            except BaseException:
                return False
        return True

    def validate_search_dict(self, d):
        for k in d:
            if not isinstance(k, str):
                return False
            if not self.validate(d[k]):
                return False
        return True

    @tornado.gen.coroutine
    def create_pmid_files(
            self,
            pmids,
            username,
            collection,
            token,
            already_created):
        for p_raw in pmids:
            p = int(p_raw)
            if p not in already_created:
                pmid_data = {
                    "message": "Add {0}.json".format(p),
                    "content": encode_for_github(
                        {})}
                yield self.github_request(PUT,
                                          "repos/{0}/{1}/contents/{2}.json".format(
                                              username,
                                              get_repo_name_from_collection(
                                                  collection),
                                              p),
                                          token,
                                          pmid_data)
                already_created.add(p)

    def process(self, response, args):
        # Create an empty file for each PMID, and add to the metadata file.
        if not self.validate(args["unmapped_pmids"]):
            response["success"] = 0
            response["description"] = "List of PMIDs is invalid."
            return response
        if not self.validate_search_dict(args["search_to_pmids"]):
            response["success"] = 0
            response["description"] = "Dictionary mapping search strings to PMIDs is invalid."
            return response
        failures = self.add_new_pmids(
            args['search_to_pmids'],
            args['unmapped_pmids'])
        if len(failures) > 0:
            response['failures'] = json.dumps(failures)

        username = get_github_username_from_api_key(args["key"])

        # Get PMIDs that are already added.
        get_metadata = yield self.github_request(
            GET, "repos/{0}/{1}/contents/metadata.json".format(
                username, get_repo_name_from_collection(
                    args["collection_name"])), args["github_token"])

        collection_metadata = decode_from_github(
            get_metadata["content"])
        current_pmids = set(collection_metadata["unmapped_pmids"])
        for k in collection_metadata["search_to_pmids"]:
            current_pmids.update(collection_metadata["search_to_pmids"][k])

        # Handle unmapped PMIDs.
        yield self.create_pmid_files(
            args["unmapped_pmids"],
            username,
            args["collection_name"],
            args["github_token"],
            current_pmids)
        collection_metadata["unmapped_pmids"] = list(
            set(collection_metadata["unmapped_pmids"]) | set(args["unmapped_pmids"]))

        # Handle other PMIDs.
        for k in args["search_to_pmids"]:
            yield self.create_pmid_files(
                args["search_to_pmids"][k],
                username,
                args["collection_name"],
                args["github_token"],
                current_pmids)
            if k not in collection_metadata["search_to_pmids"]:
                collection_metadata["search_to_pmids"][k] = []
            collection_metadata["search_to_pmids"][k] = list(
                set(collection_metadata["search_to_pmids"][k]) | set(args["search_to_pmids"][k]))

        metadata_data = {
            "message": "Update metadata.json",
            "content": encode_for_github(collection_metadata),
            "sha": get_metadata["sha"]}

        yield self.github_request(PUT,
                                  "repos/{0}/{1}/contents/metadata.json".format(
                                      username,
                                      get_repo_name_from_collection(
                                          args["collection_name"])),
                                  args["github_token"],
                                  metadata_data)

        return response


class ToggleExclusionFromCollectionEndpointHandler(BaseHandler):
    """ Exclude an experiment or all experiments for a PMID from the collection. """

    parameters = {
        "collection_name": {
            "type": str,
            "description": "The name of this collection, as seen and defined by the user."
        },
        "github_token": {
            "type": str
        },
        "pmid": {
            "type": int
        },
        "experiment_id": {
            "type": int,
            "description": "Include if removing just one experiment.",
            "default": -1
        },
        "exclusion_criterion": {
            "type": str
        },
        "exclude": {
            "type": int
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # Add the excluded experiment to the file for this PMID.
        collection_name = get_repo_name_from_collection(
            args['collection_name'])
        user = get_github_username_from_api_key(args['key'])

        article_values = yield self.github_request(
            GET, "repos/{0}/{1}/contents/{2}.json".format(
                user, collection_name, args['pmid']), args["github_token"])

        collection_article = decode_from_github(article_values['content'])
        sha = article_values['sha']

        if args['experiment_id'] == -1:
            # excluding an entire PMID
            collection_article['excluded_flag'] = args['exclude']
            if args['exclude']:
                collection_article['exclusion_reason'] = args['exclusion_criterion']

        else:
            # Excluding an entire PMID
            if args['experiment_id'] not in collection_article['experiments']:
                collection_article['experiments'][args['experiment_id']] = {}
            collection_article['experiments'][args['experiment_id']
                                              ]['excluded_flag'] = args['exclude']
            if args['exclude']:
                collection_article['experiments'][args['experiment_id']
                                                  ]['exclusion_reason'] = args['exclusion_criterion']

        data = {
            "message": "Update {0}.json".format(args['pmid']),
            "content": encode_for_github(collection_article),
            "sha": sha}
        # Now set the content of the file to the updated collection_article
        update_article = yield self.github_request(PUT,
                                                   "repos/{0}/{1}/contents/{2}.json".format(user,
                                                                                            collection_name,
                                                                                            args['pmid']),
                                                   args["github_token"],
                                                   data)

        return response


class GetUserCollectionsEndpointHandler(BaseHandler):
    """ Get the Brainspell collections owned by this user, including the PMIDs that are included. """

    parameters = {
        "github_token": {
            "type": str
        },
        "contributors": {
            "type": int,
            "default": 0,
            "description": "1 if you want contributors information for each repo, 0 otherwise."
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # Get all repositories owned by this user, and return the names that start with
        # brainspell-neo-collection.

        user = get_github_username_from_api_key(args['key'])
        brainspell_repos = []
        contributors_info = {}
        page_number = 1
        more_repos = True

        while more_repos:
            repos_list = yield self.github_request(GET,
                                                   "user/repos?per_page=100&page={0}".format(page_number),
                                                   args["github_token"],
                                                   {"affiliation": "owner"})

            if len(repos_list) == 0:
                more_repos = False

            for repo in repos_list:
                if repo["name"][:len("brainspell-neo-collection-")
                                ] == "brainspell-neo-collection-":
                    brainspell_repos.append((repo["name"], repo["url"]))
                    if args["contributors"] != 0:
                        contributors_req = yield self.github_request(
                            GET, repo["contributors_url"].replace(
                                "https://api.github.com/", ""), args["github_token"])
                        contributors_info[repo["name"]] = [{
                            "login": c["login"],
                            "avatar_url": c["avatar_url"]
                        } for c in contributors_req]

            page_number += 1

        user_collections = []

        for name, url in brainspell_repos:
            repo_req = yield self.github_request(GET,
                                                 url.replace(
                                                     "https://api.github.com/",
                                                     "") + "/contents/metadata.json",
                                                 args["github_token"])
            repo_meta = decode_from_github(repo_req["content"])

            # Convert PeeWee article object to dict
            def parse_article_object(article_object):
                return {
                    "title": article_object.title,
                    "reference": article_object.reference,
                    "authors": article_object.authors,
                    "pmid": article_object.pmid
                }

            unmapped_article_dicts = []

            for p in repo_meta["unmapped_pmids"]:
                try:
                    obj = next(get_article_object(p))
                    unmapped_article_dicts.append(parse_article_object(obj))
                except BaseException:
                    if "failed_to_fetch" not in response:
                        response["failed_to_fetch"] = []
                    response["failed_to_fetch"].append(p)

            search_to_articles = {}
            for k in repo_meta["search_to_pmids"]:
                search_to_articles[k] = []
                for p in repo_meta["search_to_pmids"][k]:
                    try:
                        obj = next(get_article_object(p))
                        search_to_articles[k].append(parse_article_object(obj))
                    except BaseException:
                        if "failed_to_fetch" not in response:
                            response["failed_to_fetch"] = []
                        response["failed_to_fetch"].append(p)

            single_collection = {
                "name": name[len("brainspell-neo-collection-"):],
                "description": repo_meta["description"],
                "unmapped_articles": unmapped_article_dicts,
                "search_to_articles": search_to_articles
            }
            if args["contributors"] != 0:
                single_collection["contributors"] = contributors_info[name]
            user_collections.append(single_collection)

        response["collections"] = user_collections
        return response


class EditGlobalArticleEndpointHandler(BaseHandler):
    """ Edit information for this article, either collection-specific or global. """

    parameters = {
        "github_token": {
            "type": str
        },
        "pmid": {
            "type": int
        },
        "experiments": {
            "type": json.loads,
            "description": "A list of experiment dictionaries, in the same format that we send, only including global keys."
        },
        "subjects": {
            "type": int,
            "description": "The number of subjects for the entire article. Experiment specific values should be in the experiments argument."
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    default_exp = {
        "caption": "",
        "locations": [],
        "descriptors": [],
        "contrast": "",
        "space": "",
        "effect": ""
    }

    valid_space = {
        "mni", "talairach", "other", "unknown", ""
    }

    @tornado.gen.coroutine
    def validate_experiments(self, exp_list):
        """ Validate and fill in the blanks for the experiments dictionary. """
        if not isinstance(exp_list, list):
            self.abort("The experiments argument should be a list.")

        for exp in exp_list:
            if "id" not in exp:
                self.abort("All experiments must have IDs.")
            for k in exp:
                # Don't throw an error for the ID or the vestigial title field.
                if k not in exp and k != "id" and k != "title":
                    self.abort("Unexpected key in experiment: {0}".format(k))
            for k in EditGlobalArticleEndpointHandler.default_exp:
                if k not in exp:
                    exp[k] = EditGlobalArticleEndpointHandler.default_exp[k]
            s = exp["space"].lower().strip()
            if s not in EditGlobalArticleEndpointHandler.valid_space:
                self.abort("Invalid value for space.")
            # Ensure lowercase.
            exp["space"] = s
            # Gracefully handle non-integer values for experiment locations.
            clean_locations = []
            for l in exp["locations"]:
                r = l.split(",")
                clean_l = []
                for v in r:
                    try:
                        clean_l.append(str(int(v)))
                    except BaseException:
                        clean_l.append("")
                clean_locations.append(",".join(clean_l))
            exp["locations"] = clean_locations

    def process(self, response, args):
        # Update global information in our database.
        # Not in database: coordinate_space, effect_type, contrast, key-value
        # pairs

        article = next(get_article_object(args["pmid"]))
        yield self.validate_experiments(args["experiments"])

        metadata = json.loads(article.metadata)
        if metadata is None:
            # Gracefully handle null metadata.
            metadata = {}

        metadata["nsubjects"] = args["subjects"]

        experiments = json.loads(article.experiments)
        if experiments is None:
            # Gracefully handle null experiments.
            experiments = []

        # Map from experiment ID to index.
        mapping = {}
        for i in range(len(experiments)):
            mapping[experiments[i]["id"]] = i

        for exp in args["experiments"]:
            if exp["id"] not in mapping:
                experiments.append({})
                mapping[exp["id"]] = len(experiments) - 1

            idx = mapping[exp["id"]]
            for k in exp:
                experiments[idx][k] = exp[k]

        replace_experiments(args['pmid'], json.dumps(experiments))
        replace_metadata(args['pmid'], json.dumps(metadata))

        return response


class EditLocalArticleEndpointHandler(BaseHandler):
    """ Edit information for this article, either collection-specific or global. """

    parameters = {
        "collection_name": {
            "type": str,
            "description": "The name of a collection, as seen and defined by the user."
        },
        "github_token": {
            "type": str
        },
        "pmid": {
            "type": int
        },
        "key_value_pairs": {
            "type": json.loads,
            "description": "Map<experiment_id,Map<key,value>>",
            "default": "{}"
        },
        "exclusion_reasons": {
            "type": json.loads,
            "description": "Map<experiment_id,Reason for excluding an experiment or PMID>",
            "default": "{}"
        },

    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # See what fields are included in the edit_contents dictionary, and update each provided
        # field in the appropriate place, whether on GitHub or otherwise.
        collection_name = get_repo_name_from_collection(
            args['collection_name'])
        user = get_github_username_from_api_key(args['key'])

        article_values = yield self.github_request(
            GET, "repos/{0}/{1}/contents/{2}.json".format(
                user, collection_name, args['pmid']), args["github_token"])

        # Update the Individual Article page for the corresponding PMID
        article_content = decode_from_github(article_values["content"])

        sha = article_values['sha']
        # Initialize structures

        # Execute experiment specific key-value updates
        for exp_id, kv in args['key_value_pairs'].items():
            if int(exp_id) > 0:

                if not article_content.get('experiments'):
                    article_content['experiments'] = {}
                if exp_id not in article_content['experiments']:
                    article_content['experiments'][exp_id] = {}
                if "key_value_pairs" not in article_content['experiments'][exp_id]:
                    article_content['experiments'][exp_id]['key_value_pairs'] = {}
                article_content['experiments'][exp_id]['key_value_pairs'] = kv
                # Key value pairs being added imply experiment is not excluded
                # (@Katie)
                article_content['experiments'][exp_id]['excluded_flag'] = 0

            else:
                pass  # Key value pairs must be associated with an experiment

        for exp_id, exclusion_criteria in args['exclusion_reasons'].items():
            if int(exp_id) > 0:
                if not article_content.get("experiments"):
                    article_content['experiments'] = {}

                if exp_id not in article_content['experiments']:
                    article_content['experiments'][exp_id] = {}

                article_content['experiments'][exp_id]['excluded_flag'] = 1

            else:
                article_content['excluded_flag'] = 1

        data = {
            "message": "Update {0}.json".format(args['pmid']),
            "content": encode_for_github(article_content),
            "sha": sha}
        # Update the contents of the JSON file with new key value pairs

        key_value_update = yield self.github_request(
            PUT, "repos/{0}/{1}/contents/{2}.json" .format(
                user, collection_name, args['pmid']), args["github_token"], data)

        return response


class GetArticleFromCollectionEndpointHandler(BaseHandler):
    """ Get the collection-specific information for this article. """

    parameters = {
        "collection_name": {
            "type": str,
            "description": "The name of this collection, as seen and defined by the user."
        },
        "github_token": {
            "type": str
        },
        "pmid": {
            "type": str
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # Get the PMID file from the GitHub repository for this collection.

        collection_name = get_repo_name_from_collection(
            args['collection_name'])
        user = get_github_username_from_api_key(args['key'])
        collection_values = yield self.github_request(
            GET, "repos/{0}/{1}/contents/{2}.json".format(
                user, collection_name, args["pmid"]), args["github_token"])

        response["article_info"] = decode_from_github(
            collection_values["content"])

        return response


class AddKeyValuePairEndpointHandler(BaseHandler):
    """ Add a key-value pair for an experiment. """

    parameters = {
        "collection_name": {
            "type": str,
            "description": "The name of this collection, as seen and defined by the user."
        },
        "github_token": {
            "type": str
        },
        "pmid": {
            "type": int
        },
        "experiment_id": {
            "type": int
        },
        "k": {
            "type": str,
            "description": "The key for the key-value pair being added to this experiment."
        },
        "v": {
            "type": str,
            "description": "The value for the key-value pair being added to this experiment."
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # Edit the PMID file from the GitHub repository for this collection.
        collection_name = get_repo_name_from_collection(
            args['collection_name'])
        user = get_github_username_from_api_key(args['key'])

        article_values = yield self.github_request(
            GET, "repos/{0}/{1}/contents/{2}.json".format(
                user, collection_name, args['pmid']), args["github_token"])
        article_content = decode_from_github(article_values["content"])

        sha = article_values['sha']
        # Initialize structures
        if not article_content.get('experiments'):
            article_content['experiments'] = {}
        if args['experiment_id'] not in article_content['experiments']:
            article_content['experiments'][args['experiment_id']] = {}
        if "key_value_pairs" not in article_content['experiments'][args['experiment_id']]:
            article_content['experiments'][args['experiment_id']
                                           ]['key_value_pairs'] = {}
        article_content['experiments'][args['experiment_id']
                                       ]['key_value_pairs'][args['k']] = args['v']
        # Key value pairs being added imply experiment is not excluded (@Katie)
        article_content['experiments'][args['experiment_id']
                                       ]['excluded_flag'] = 0

        data = {
            "message": "Update {0}.json".format(args['pmid']),
            "content": encode_for_github(article_content),
            "sha": sha}

        # Update the contents of the JSON file with new key value pairs
        yield self.github_request(PUT,
                                  "repos/{0}/{1}/contents/{2}.json".format(user,
                                                                           collection_name,
                                                                           args['pmid']),
                                  args["github_token"],
                                  data)

        return response


# BEGIN: search API endpoints


class QueryEndpointHandler(BaseHandler):
    """ Endpoint to handle search queries. Return 10 results at a time. """
    parameters = {
        "q": {
            "type": str,
            "default": "",
            "description": "The query to search for."
        },
        "start": {
            "type": int,
            "default": 0,
            "description": START_DESC
        },
        "req": {
            "type": str,
            "default": "t",
            "description": REQ_DESC
        }
    }

    endpoint_type = Endpoint.PULL_API

    def process(self, response, args):
        database_dict = {}
        results = formatted_search(args["q"], args["start"], args["req"])
        output_list = []
        for article in results:
            try:
                article_dict = {}
                article_dict["id"] = article.pmid
                article_dict["title"] = article.title
                article_dict["authors"] = article.authors
                output_list.append(article_dict)
            except BaseException:
                pass
        response["articles"] = output_list
        if len(results) == 0:
            response["start_index"] = -1
            # returns -1 if there are no results;
            # UI can always calculate (start, end) with (start_index + 1, start_index + 1 + len(articles))
            # TODO: consider returning the start/end indices for the range of
            # articles returned instead
        else:
            response["start_index"] = args["start"]
        return response


class CoordinatesEndpointHandler(BaseHandler):
    """
    API endpoint to fetch coordinates from all articles that match a query.
    Return 200 sets of coordinates at a time.
    """

    parameters = {
        "q": {
            "type": str,
            "default": "",
            "description": "The search query to return the coordinates for."
        },
        "start": {
            "type": int,
            "default": 0,
            "description": START_DESC
        },
        "req": {
            "type": str,
            "default": "t",
            "description": REQ_DESC
        }
    }

    endpoint_type = Endpoint.PULL_API

    def process(self, response, args):
        database_dict = {}
        results = formatted_search(args["q"], args["start"], args["req"], True)
        output_list = []
        for article in results:
            try:
                article_dict = {}
                experiments = json.loads(article.experiments)
                for c in experiments:  # get the coordinates from the experiments
                    output_list.extend(c["locations"])
            except BaseException:
                pass
        response["coordinates"] = output_list
        return response


class RandomQueryEndpointHandler(BaseHandler):
    """ Return five random articles (for use on Brainspell's front page) """

    parameters = {}

    endpoint_type = Endpoint.PULL_API

    def process(self, response, args):
        database_dict = {}
        results = random_search()
        output_list = []
        for article in results:
            try:
                article_dict = {}
                article_dict["id"] = article.pmid
                article_dict["title"] = article.title
                article_dict["authors"] = article.authors
                output_list.append(article_dict)
            except BaseException:
                pass
        response["articles"] = output_list
        return response


class AddArticleFromPmidEndpointHandler(BaseHandler):
    """ Add an article to our database via PMID (for use on the search page) """
    parameters = {
        "new_pmid": {
            "type": str,
            "description": PMID_DESC
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        add_pmid_article_to_database(args["new_pmid"])
        return response


# BEGIN: article API endpoints


class ArticleEndpointHandler(BaseHandler):
    """
    Return the contents of an article, given a PMID.
    Called by the view-article page.
    """

    parameters = {
        "pmid": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PULL_API

    def process(self, response, args):
        try:
            article = next(get_article_object(args["pmid"]))
            response["timestamp"] = article.timestamp
            response["abstract"] = article.abstract
            response["authors"] = article.authors
            response["doi"] = article.doi
            response["experiments"] = article.experiments
            response["metadata"] = article.metadata
            response["neurosynthid"] = article.neurosynthid
            response["pmid"] = article.pmid
            response["reference"] = article.reference
            response["title"] = article.title
            response["id"] = article.uniqueid
        except BaseException:
            response["success"] = 0
        return response


class BulkAddEndpointHandler(BaseHandler):
    """
    Add a large number of articles to our database at once,
    by parsing a file that is sent to us in a JSON format.
    """

    parameters = {}

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # TODO: add better file parsing function
        try:
            file_body = self.request.files['articlesFile'][0]['body'].decode(
                'utf-8')
            contents = json.loads(file_body)
            if isinstance(contents, list):
                clean_articles = clean_bulk_add(contents)
                add_bulk(clean_articles)
                response["success"] = 1
            else:
                # data is malformed
                response["success"] = 0
        except BaseException:
            response["success"] = 0
            response["description"] = "You must POST a file with the parameter name 'articlesFile' to this endpoint."
        return response


class SetArticleAuthorsEndpointHandler(BaseHandler):
    """ Edit the authors of an article. """

    parameters = {
        "pmid": {
            "type": str
        },
        "authors": {
            "type": str,
            "description": "The string to set as the 'authors' for this article."
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        update_authors(args["pmid"], args["authors"])
        return response


class ToggleStereotaxicSpaceVoteEndpointHandler(BaseHandler):
    """ Toggle a user's vote for the stereotaxic space of an article. """

    parameters = {
        "pmid": {
            "type": str
        },
        "space": {
            "type": str,
            "description": "Must be 'mni' or 'talairach' without quotes."
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        space = args["space"].lower()
        if space == "mni" or space == "talairach":
            vote_stereotaxic_space(
                args["pmid"],
                args["space"],
                get_github_username_from_api_key(
                    args["key"]))
        else:
            response["success"] = 0
            response["description"] = "Invalid value for 'space' parameter."
        return response


class NumberOfSubjectsVoteEndpointHandler(BaseHandler):
    """ Place a vote for the number of subjects for an article. """

    parameters = {
        "pmid": {
            "type": str
        },
        "subjects": {
            "type": int,
            "description": "The number of subjects that should be set for this article."
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        vote_number_of_subjects(
            args["pmid"],
            args["subjects"],
            get_github_username_from_api_key(
                args["key"]))
        return response


class AddExperimentsTableViaTextEndpointHandler(BaseHandler):
    """
    Add a table of experiment coordinates via text.
    Used on the view-article page.
    """

    parameters = {
        "values": {
            "type": str,
            "description": "Takes a CSV formatted string of coordinates; i.e., x, y, z separated by commas, and each coordinate separated by a newline."
        },
        "pmid": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        add_table_through_text_box(args["pmid"], args["values"])
        return response


class ToggleUserVoteEndpointHandler(BaseHandler):
    """ Endpoint for a user to vote on an article tag. """
    parameters = {
        "topic": {
            "type": str,
            "description": "The name of the tag to place a vote for."
        },
        "pmid": {
            "type": str
        },
        "direction": {
            "type": str,
            "description": "The direction that the user clicked in. Will toggle; i.e., if the user votes up on an article they've already upvoted, then it will clear the vote."
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        username = get_github_username_from_api_key(args["key"])
        toggle_vote(args["pmid"], args["topic"], username, args["direction"])
        return response

# BEGIN: table API endpoints


class ToggleUserTagOnArticleEndpointHandler(BaseHandler):
    """ Toggle a user tag on an article in our database. """

    parameters = {
        "pmid": {
            "type": str
        },
        "tag_name": {
            "type": str,
            "description": "The name of the tag to add."
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        pmid = args["pmid"]
        user_tag = args["tag_name"]
        username = get_github_username_from_api_key(args["key"])
        toggle_user_tag(user_tag, pmid, username)
        return response


class UpdateTableVoteEndpointHandler(BaseHandler):
    """ Update the vote on a tag for an experiment table. """

    parameters = {
        "tag_name": {
            "type": str
        },
        "direction": {
            "type": str
        },
        "experiment": {
            "type": int
        },
        "pmid": {
            "type": str
        },
        "column": {
            "type": str,
            "description": "The column to place the vote under. Options are 'T' for tasks, 'B' for behavioral, and 'C' for cognitive."
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        username = get_github_username_from_api_key(args["key"])
        c = args["column"]
        if c != "T" and c != "B" and c != "C":
            response["success"] = 0
            response["description"] = "That is not a valid option for the column parameter."
        else:
            update_table_vote(
                args["tag_name"],
                args["direction"],
                args["table_num"],
                args["pmid"],
                c,
                username)
        return response


class FlagTableEndpointHandler(BaseHandler):
    """ Flag a table as inaccurate. """

    parameters = {
        "pmid": {
            "type": str
        },
        "experiment": {
            "type": int
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        flag_table(args["pmid"], args["experiment"])
        return response


class EditTableTitleCaptionEndpointHandler(BaseHandler):
    """ Edit the title and caption for an experiment table. """

    parameters = {
        "pmid": {
            "type": str
        },
        "experiment": {
            "type": int
        },
        "title": {
            "type": str
        },
        "caption": {
            "type": str,
            "default": ""
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        edit_table_title_caption(
            args["pmid"],
            args["experiment"],
            args["title"],
            args["caption"])
        return response


class DeleteRowEndpointHandler(BaseHandler):
    """ Delete a row of coordinates from an experiment table. """

    parameters = {
        "pmid": {
            "type": str
        },
        "experiment": {
            "type": int
        },
        "row_number": {
            "type": int
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        delete_row(args["pmid"], args["experiment"], args["row"])
        return response


class SplitTableEndpointHandler(BaseHandler):
    """
    Split a table of coordinates for an experiment into two
    separate tables.
    """

    parameters = {
        "pmid": {
            "type": str
        },
        "experiment": {
            "type": int
        },
        "row_number": {
            "type": int
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        split_table(args["pmid"], args["experiment"], args["row"])
        return response


class UpdateRowEndpointHandler(BaseHandler):
    """ Update a row of coordinates in an experiment table. """

    parameters = {
        "pmid": {
            "type": str
        },
        "experiment": {
            "type": int
        },
        "coordinates": {
            "type": json.loads,
            "description": "Takes a JSON array of three or four coordinates. (The fourth is z-effective.)"
        },
        "row_number": {
            "type": int
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        coords = args["coordinates"]
        if len(coords) == 3 or len(coords) == 4:
            update_coordinate_row(
                args["pmid"],
                args["experiment"],
                coords,
                args["row_number"])
        else:
            response["success"] = 0
            response["description"] = "Wrong number of coordinates."
        return response


class AddRowEndpointHandler(BaseHandler):
    """ Add a single row of coordinates to an experiment table. """

    parameters = {
        "pmid": {
            "type": str
        },
        "experiment": {
            "type": int
        },
        "coordinates": {
            "type": json.loads,
            "description": "Takes a JSON array of three or four coordinates. (The fourth is z-effective.)"
        },
        "row_number": {
            "type": int,
            "default": -1,
            "description": "The index that this row should be located at in the table. Defaults to the end of the table."
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        coords = args["coordinates"]
        if len(coords) == 3 or len(coords) == 4:
            add_coordinate_row(
                args["pmid"],
                args["experiment"],
                coords,
                args["row_number"])
        else:
            response["success"] = 0
            response["description"] = "Wrong number of coordinates."
        return response


class GetOaPdfEndpointHandler(BaseHandler):
    """ Get the PDF corresponding to a DOI. """

    parameters = {
        "doi": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PULL_API
    handle_finishing = True

    @run_on_executor
    def get_pdf_bytes(self, url):
        response = requests.get(url).content
        return response

    def process(self, response, args):
        doi = args['doi']
        unpaywallURL = 'https://api.unpaywall.org/v2/{doi}?email=keshavan@berkeley.edu'.format(
            doi=doi)
        req = requests.get(unpaywallURL)
        data = req.json()
        if data['best_oa_location']:
            try:
                # get pdf
                pdf_url = data['best_oa_location']['url_for_pdf']
                pdf_bytes = yield self.get_pdf_bytes(pdf_url)
                self.set_header("Content-Type", "application/pdf")
                self.write(pdf_bytes)
                self.finish()
            except Exception as e:
                response['success'] = 0
                response['error'] = str(e)
                self.finish_async(response)
        else:
            response['success'] = 0
            self.finish_async(response)
