# JSON API classes

from article_helpers import *
from search import *
from user_accounts import *
from base_handler import *

# BEGIN: search API endpoints

# API endpoint to handle search queries; returns 10 results at a time

class QueryEndpointHandler(BaseHandler):
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


# API endpoint to fetch coordinates from all articles that match a query;
# returns 200 sets of coordinates at a time
class CoordinatesEndpointHandler(BaseHandler):
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


# API endpoint that returns five random articles; used on the front page
# of Brainspell
class RandomQueryEndpointHandler(BaseHandler):
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

# BEGIN: article API endpoints

# API endpoint to get the contents of an article (called by the
# view-article page)


class ArticleEndpointHandler(BaseHandler):
    parameters = {
        "pmid": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PULL_API

    def process(self, response, args):
        try:
            article = next(get_article(args["pmid"]))
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

# API endpoint corresponding to BulkAddHandler


class BulkAddEndpointHandler(BaseHandler):
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
        except:
            response["success"] = 0
            response["description"] = "You must POST a file with the parameter name 'articlesFile' to this endpoint."
        return response

# fetch PubMed and Neurosynth data using a user specified PMID, and add
# the article to our database


class AddArticleEndpointHandler(BaseHandler):
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

# edit the authors of an article


class SetArticleAuthorsEndpointHandler(BaseHandler):
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

# endpoint for a user to vote on an article tag


class ToggleUserVoteEndpointHandler(BaseHandler):
    parameters = {
        "key": {
            "type": str,
            "default": ""
        },
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

# vote on a table tag

class UpdateTableVoteEndpointHandler(BaseHandler):
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
        "id": {
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
        update_table_vote(args["tag_name"], args["direction"], args["table_num"], args["id"], args["column"], args["username"])
        return response

# flag a table as inaccurate


class FlagTableEndpointHandler(BaseHandler):
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

# delete row from experiment table


class DeleteRowEndpointHandler(BaseHandler):
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

# split experiment table


class SplitTableEndpointHandler(BaseHandler):
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

# add one row of coordinates to an experiment table


class AddRowEndpointHandler(BaseHandler):
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
