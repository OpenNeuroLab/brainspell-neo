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
import tornado.gen
from base64 import b64decode, b64encode

REQ_DESC = "The fields to search through. 'x' is experiments, 'p' is PMID, 'r' is reference, and 't' is title + authors + abstract."
START_DESC = "The offset of the articles to show; e.g., start = 10 would return results 11 - 20."

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
            user_data = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": "token " +
                    params["access_token"][0]})
            user = user_data.json()
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
        "search_strings": {
            "type": json.loads,
            "default": "[]"},
        "github_token": {
            "type": str}}

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def validate(self, j):
        # Validate a list of strings. If reused, move to another file.
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
        v4 = self.validate(args["search_strings"])

        if not (v1 and v2 and v3 and v4):
            response["success"] = 0
            response["description"] = "One of the JSON inputs was invalid."
            return response

        # Create the repository.

        repo_data = {
            "name": get_repo_name_from_collection(args["collection_name"]),
            "description": args["description"],
        }

        result = requests.post(
            "https://api.github.com/user/repos", json.dumps(repo_data),
            headers={
                "Authorization": "token " + args["github_token"]
            })

        if result.status_code != 201:
            response["success"] = 0
            response["description"] = "Creating the repository failed."

            return response

        # Create the metadata.json file.

        username = get_github_username_from_api_key(args["key"])

        collection_metadata = json.dumps({
            "description": args["description"],
            "pmids": [],
            "exclusion_criteria": args["exclusion_criteria"],
            "inclusion_criteria": args["inclusion_criteria"],
            "tags": args["tags"],
            "search_strings": args["search_strings"]
        })

        metadata_data = {"message": "Add metadata.json", "content": b64encode(
            collection_metadata.encode('utf-8')).decode('utf-8')}

        add_metadata = requests.put(
            "https://api.github.com/repos/" +
            username +
            "/" +
            get_repo_name_from_collection(
                args["collection_name"]) +
            "/contents/metadata.json",
            json.dumps(metadata_data),
            headers={
                "Authorization": "token " +
                args["github_token"]})

        if add_metadata.status_code != 201:
            response["success"] = 0
            response["description"] = "Creating the metadata.json file failed."
            return response

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
        # TODO: Make necessary GitHub requests.
        # Get the metadata file from the GitHub repository for this collection.
        raise NotImplementedError
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
        "pmids": {
            "type": json.loads,
            "description": "A JSON-serialized list of PMIDs to add to this collection.",
            "default": "[]"
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

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

    def process(self, response, args):
        # Create an empty file for each PMID, and add to the metadata file.
        # TODO: Add PMIDs to the database if they're not already
        # present.
        if not self.validate(args["pmids"]):
            response["success"] = 0
            response["description"] = "List of PMIDs is invalid."
            return response

        username = get_github_username_from_api_key(args["key"])
        pmid_data = {"message": "Add metadata.json", "content": b64encode(
            "{{}}".encode('utf-8')).decode('utf-8')}

        # Get PMIDs that are already added.
        get_metadata = requests.get(
            "https://api.github.com/repos/" +
            username +
            "/" +
            get_repo_name_from_collection(
                args["collection_name"]) +
            "/contents/metadata.json",
            headers={
                "Authorization": "token " +
                args["github_token"]})

        collection_metadata = json.loads(
            b64decode(get_metadata.json()["content"]).decode('utf-8'))

        current_pmids = set(collection_metadata["pmids"])

        added_pmid = False

        for p_raw in args["pmids"]:
            p = int(p_raw)
            if p not in current_pmids:
                added_pmid = True
                add_pmid = requests.put(
                    "https://api.github.com/repos/" +
                    username +
                    "/" +
                    get_repo_name_from_collection(
                        args["collection_name"]) +
                    "/contents/" + str(p) + ".json",
                    json.dumps(pmid_data),
                    headers={
                        "Authorization": "token " +
                        args["github_token"]})

                if add_pmid.status_code != 201:
                    response["success"] = 0
                    response["description"] = "Creating the {0}.json file failed.".format(
                        p)
                    return response
                current_pmids.add(p)

        if not added_pmid:
            return response

        collection_metadata["pmids"] = list(current_pmids)

        metadata_data = {
            "message": "Update metadata.json",
            "content": b64encode(
                json.dumps(collection_metadata).encode('utf-8')).decode('utf-8'),
            "sha": get_metadata.json()["sha"]}

        add_metadata = requests.put(
            "https://api.github.com/repos/" +
            username +
            "/" +
            get_repo_name_from_collection(
                args["collection_name"]) +
            "/contents/metadata.json",
            json.dumps(metadata_data),
            headers={
                "Authorization": "token " +
                args["github_token"]})

        if add_metadata.status_code != 200:
            response["success"] = 0
            response["description"] = "Updating the metadata.json file failed."
            return response

        return response


class ExcludeFromCollectionEndpointHandler(BaseHandler):
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
        "experiment": {
            "type": int,
            "description": "Include if removing just one experiment.",
            "default": -1
        },
        "exclusion_criterion": {
            "type": str
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # TODO: Make necessary GitHub requests.
        # Add the excluded experiment to the file for this PMID.
        raise NotImplementedError
        return response


class GetUserCollectionsEndpointHandler(BaseHandler):
    """ Get the Brainspell collections owned by this user. """

    parameters = {
        "github_token": {
            "type": str
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # TODO: Make necessary GitHub requests.
        # Get all repositories owned by this user, and return the names that start with
        # brainspell-neo-collection.
        raise NotImplementedError
        return response


class EditArticleEndpointHandler(BaseHandler):
    """ Edit information for this article, either collection-specific or global. """

    parameters = {
        "collection_name": {
            "type": str,
            "description": "The name of a collection, as seen and defined by the user.",
            "default": ""
        },
        "github_token": {
            "type": str
        },
        "pmid": {
            "type": str
        },
        "edit_contents": {
            "type": json.loads,
            "description": "Data that should be changed in the user's collections and Brainspell's version."
        }
    }

    api_version = 2
    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # TODO: Make necessary GitHub requests.
        # See what fields are included in the edit_contents dictionary, and update each provided
        # field in the appropriate place, whether on GitHub or otherwise.
        raise NotImplementedError
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
        "experiment": {
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
        # TODO: Make necessary GitHub requests.
        # Edit the PMID file from the GitHub repository for this collection.
        raise NotImplementedError
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
    asynchronous = True

    @run_on_executor
    def get_pdf_bytes(self, url):
        response = requests.get(url).content
        return response

    @tornado.gen.coroutine
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
