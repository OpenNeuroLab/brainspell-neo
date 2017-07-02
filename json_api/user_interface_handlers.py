# handlers for the user-facing website

import hashlib
import json
import os
from base64 import b64encode

from article_helpers import *
from base_handler import *
from user_account_helpers import *


class MainHandler(BaseHandler):
    """ The front page of Brainspell. """

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

    def get(self):
        article_id = -1
        try:
            article_id = self.get_query_argument("id")
        except BaseException:
            self.redirect("/")  # id wasn't passed; redirect to home page
        article_dict = {
            "article_id": article_id
        }
        self.render_with_user_info(
            "static/html/view-article.html", article_dict)


class ContributionHandler(BaseHandler):
    """ Show the user how they can contribute to the Brainspell platform. """

    def get(self):
        self.render_with_user_info('static/html/contribute.html')


class BulkAddHandler(BaseHandler):
    """
    Take a file in JSON format and add the articles to our database.
    (called from the /contribute page)
    This handler is deprecated; please use the JSON API instead.
    """

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
