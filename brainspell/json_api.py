# JSON API classes

import brainspell
from article_helpers import *
from base_handler import *
from search_helpers import *
from user_account_helpers import *

REQ_DESC = "The fields to search through. 'x' is experiments, 'p' is PMID, 'r' is reference, and 't' is title + authors + abstract."
START_DESC = "The offset of the articles to show; e.g., start = 10 would return results 11 - 20."


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
            article = get_article_object(args["pmid"])
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
