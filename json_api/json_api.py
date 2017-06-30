# JSON API classes

from article_helpers import *
from base_handler import *
from search import *
from user_accounts import *

# BEGIN: search API endpoints

class QueryEndpointHandler(BaseHandler):
    """ Endpoint to handle search queries. Return 10 results at a time. """
    parameters = {
        "q": {
            "type": str,
            "default": ""
        },
        "start": {
            "type": int,
            "default": 0
        },
        "req": {
            "type": str,
            "default": "t"
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
            "default": ""
        },
        "start": {
            "type": int,
            "default": 0
        },
        "req": {
            "type": str,
            "default": "t"
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


class AddArticleFromSearchPageEndpointHandler(BaseHandler):
    """ Add an article to our database via PMID (for use on the search page) """
    parameters = {
        "new_pmid": {
            "type": str
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


class AddArticleEndpointHandler(BaseHandler):
    """
    Fetch PubMed and Neurosynth data using a user-specified PMID, and add
    the article to our database.
    """

    parameters = {
        "pmid": {
            "type": str,
            "default": ""
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        article_obj = getArticleData(args["pmid"])
        request = Articles.insert(abstract=article_obj["abstract"],
                                  doi=article_obj["DOI"],
                                  authors=article_obj["authors"],
                                  experiments=article_obj["coordinates"],
                                  title=article_obj["title"])
        request.execute()
        return response


class SetArticleAuthorsEndpointHandler(BaseHandler):
    """ Edit the authors of an article. """

    parameters = {
        "pmid": {
            "type": str,
            "default": ""
        },
        "authors": {
            "type": str,
            "default": ""
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        update_authors(args["pmid"], args["authors"])
        return response

class AddExperimentsTableViaTextEndpointHandler(BaseHandler):
    """
    Add a table of experiment coordinates via text.
    Used on the view-article page.
    """

    parameters = {
        "values": {
            "type": str
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
            "default": ""
        },
        "pmid": {
            "type": str,
            "default": ""
        },
        "direction": {
            "type": str,
            "default": ""
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        username = get_github_username_from_api_key(args["key"])
        toggle_vote(args["pmid"], args["topic"], username, args["direction"])
        return response

# BEGIN: table API endpoints


# TODO: change the format that this takes for db-changes
class ChangeZScoresEndpointHandler(BaseHandler):
    """ Update the z-scores for a table within an article. """
    parameters = {
        "db-changes": {
            "type": json.loads
        },
        "pmid": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        # updates z scores
        try:
            values = args["db-changes"]
            update_z_scores(args["pmid"], values)
        except BaseException:
            response = {"success": 0}

        return response


class AddUserTagToArticleEndpointHandler(BaseHandler):
    """ Add a user tag to our database, for use in tagging articles. """

    parameters = {
        "pmid": {
            "type": str
        },
        "values": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        pmid = self.get_argument("pmid")
        user_tag = self.get_argument("values")
        add_user_tag(user_tag, pmid)
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
        "table_num": {
            "type": int
        },
        "pmid": {
            "type": int
        },
        "column": {
            "type": str
        },
        "username": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        update_table_vote(
            args["tag_name"],
            args["direction"],
            args["table_num"],
            args["pmid"],
            args["column"],
            args["username"])
        return response


class FlagTableEndpointHandler(BaseHandler):
    """ Flag a table as inaccurate. """

    parameters = {
        "pmid": {
            "type": str,
            "default": ""
        },
        "experiment": {
            "type": int
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        flag_table(args["pmid"], args["experiment"])
        return response


class DeleteRowEndpointHandler(BaseHandler):
    """ Delete a row of coordinates from an experiment table. """

    parameters = {
        "pmid": {
            "type": str,
            "default": ""
        },
        "experiment": {
            "type": int
        },
        "row": {
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
            "type": str,
            "default": ""
        },
        "experiment": {
            "type": int
        },
        "row": {
            "type": int
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        split_table(args["pmid"], args["experiment"], args["row"])
        return response


class AddRowEndpointHandler(BaseHandler):
    """ Add a single row of coordinates to an experiment table. """
    
    parameters = {
        "pmid": {
            "type": str,
            "default": ""
        },
        "experiment": {
            "type": int
        },
        "coordinates": {
            "type": str,
            "default": ""
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):
        coords = args["coordinates"].replace(" ", "")
        add_coordinate(args["pmid"], args["experiment"], coords)
        return response
