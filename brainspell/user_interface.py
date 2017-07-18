# handlers for the user-facing website

import hashlib
import json
import os
import urllib.parse
from base64 import b64encode

import github_collections
import json_api
from article_helpers import *
from base_handler import *
from user_account_helpers import *
from websockets import convert


class MainHandler(BaseHandler):
    """ The front page of Brainspell. """

    route = ""

    def get(self):
        try:  # handle failures in bulk_add
            submitted_bulk_add = int(self.get_argument("success", 0))
        except BaseException:
            submitted_bulk_add = 0
        try:
            failure_in_submitting_bulk_add = int(
                self.get_argument("failure", 0))
        except BaseException:
            failure_in_submitting_bulk_add = 0
        try:  # handle registration
            registered_right_now = int(self.get_argument("registered", 0))
        except BaseException:
            registered_right_now = 0

        custom_params = {
            "number_of_queries": get_number_of_articles(),
            "success": submitted_bulk_add,
            "failure": failure_in_submitting_bulk_add,
            # boolean that indicates if someone has just registered
            "registered": registered_right_now
        }

        self.render_with_user_info("static/html/index.html", custom_params)


class SearchHandler(BaseHandler):
    """ Search articles within Brainspell's database. """

    route = "search"

    def get(self):
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        req = self.get_query_argument("req", "t")
        custom_params = {
            "query": q,
            "start": start,
            "req": req,  # TODO: parameters like "req" and "title" need to be renamed to reflect what their values are)
        }
        self.render_with_user_info("static/html/search.html", custom_params)


class ViewArticleHandler(BaseHandler):
    """
    Display the contents of an article to the user, along with UI features for curation,
    visualization, statistics, etc.
    """

    route = "view-article"

    def get(self):
        article_id = -1
        try:
            article_id = self.get_query_argument("id")
        except BaseException:
            self.redirect("/")  # id wasn't passed; redirect to home page
        article_dict = {
            "article_id": article_id
        }

        redirect_uri = self.route + "?" + urllib.parse.urlencode({
            "id": self.get_query_argument("id")
        })

        self.render_with_user_info(
            "static/html/view-article.html",
            article_dict,
            logout_redir=redirect_uri)


class ContributionHandler(BaseHandler):
    """ Show the user how they can contribute to the Brainspell platform. """

    route = "contribute"

    def get(self):
        self.render_with_user_info('static/html/contribute.html')


class BulkAddHandler(BaseHandler):
    """
    Take a file in JSON format and add the articles to our database.
    (called from the /contribute page)
    This handler is deprecated; please use the JSON API instead.
    """

    route = "bulk-add"

    def post(self):
        file_body = self.request.files['articlesFile'][0]['body'].decode(
            'utf-8')
        contents = json.loads(file_body)
        if isinstance(contents, list):
            clean_articles = clean_bulk_add(contents)
            add_bulk(clean_articles)
            self.redirect("/?success=1")
        else:
            # data is malformed
            self.redirect("/?failure=1")


class CollectionsHandler(BaseHandler):
    """ Display the user's collections. """

    route = "collections"

    def get(self):
        if self.get_current_github_access_token():
            self.render_with_user_info("static/html/account.html")
        # if you're not authorized, redirect to OAuth
        else:
            self.redirect("/oauth?redirect_uri=/collections")


class SwaggerHandler(BaseHandler):
    """ Automatically generated swagger.json file, to document our API. """

    route = "swagger.json"

    swagger_info = {
        "swagger": "2.0",
        "info": {
            "title": "Brainspell",
            "description": "An open, human-curated repository of neuroimaging literature, with various statistical features.",
            "version": "1.0.0"},
        "host": "brainspell.herokuapp.com",
        "schemes": ["https"],
        "basePath": "/json/",
        "paths": {}}

    def parameter_object_to_swagger(name, p):
        """ Convert Brainspell parameters objects to Swagger. """

        def convert_type(t):
            """ Takes a type, and converts it to a human-readable string for Swagger. """
            if t == float:
                return "number"
            elif t == int:
                return "integer"
            # default value of string
            return "string"

        parameter_obj = {
            "name": name,
            "in": "query",
            "required": "default" not in p,
            "type": convert_type(p["type"]),
            "default": "" if "default" not in p else p["default"]
        }

        if "default" in p:
            parameter_obj["default"] = p["default"]

        if "description" in p:
            parameter_obj["description"] = p["description"]

        return parameter_obj

    # add the paths to the swagger.json file
    for name, func in [(convert(f.replace("EndpointHandler", "")), eval("json_api." + f))
                       for f in dir(json_api) if "EndpointHandler" in f] \
        + [(convert(f.replace("EndpointHandler", "")), eval("github_collections." + f))
            for f in dir(github_collections) if "EndpointHandler" in f]:

        # add parameters from each endpoint
        parameters_object = []
        for p in func.parameters:
            parameters_object.append(
                parameter_object_to_swagger(
                    p, func.parameters[p]))

        # API key isn't explicitly listed for PUSH API endpoints
        if func.endpoint_type == Endpoint.PUSH_API:
            parameters_object.append(
                parameter_object_to_swagger(
                    "key", {
                        "type": str,
                        "description": "The user's Brainspell API key."
                    }))

        operation = {
            "parameters": parameters_object,
            "produces": ["application/json"],
            "responses": {
                "default": {
                    "description": "The basic structure of a Brainspell response. Endpoint-specific JSON attributes not shown.",
                    "schema": {
                        "type": "object",
                        "required": ["success"],
                        "properties": {
                            "success": {
                                "type": "integer"}}}}}}

        swagger_info["paths"]["/" + name] = {
            "get": operation,
            "post": operation
        }

    def get(self):
        self.finish_async(self.swagger_info)
