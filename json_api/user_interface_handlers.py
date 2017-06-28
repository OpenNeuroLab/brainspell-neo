# handlers for the user-facing website

import hashlib
import json
import os
from base64 import b64encode

from article_helpers import *
from base_handler import *
from user_accounts import *

# front page


class MainHandler(BaseHandler):
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


# search page
class SearchHandler(BaseHandler):
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


class AddArticleFromSearchPageHandler(BaseHandler):
    # TODO: make JSON endpoint
    def post(self):  # allows introduction of manual article
        pmid = self.get_argument("newPMID")
        add_pmid_article_to_database(pmid)


# Handler for the textbox to add a table of coordinates on view-article page
class AddTableTextBoxHandler(BaseHandler):
    # TODO: make JSON endpoint
    def post(self):
        pmid = self.get_argument("pmid", "")
        vals = self.get_argument("values", "")
        if self.is_logged_in():
            add_table_through_text_box(pmid, vals)
        self.redirect("/view-article?id=" + pmid)


# Adds a custom user Tag to the database
class AddUserTagToArticleHandler(BaseHandler):
    # TODO: make JSON endpoint
    def post(self):
        pmid = self.get_argument("pmid")
        user_tag = self.get_argument("values")
        add_user_tag(user_tag, pmid)  # TODO: needs to verify API key
        self.redirect("/view-article?id=" + pmid)


# view-article page
class ArticleHandler(BaseHandler):
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

    def post(self):  # TODO: make its own endpoint; does not belong in this handler
        # right now, this updates z scores
        article_id = self.get_body_argument('id')
        email = self.get_current_email()
        values = ""

        try:  # TODO: get rid of try/catch and write correctly
            values = self.get_body_argument("dbChanges")
            values = json.loads(values)  # z-values in dictionary
            print(values)
        except BaseException:
            pass
        if values:
            update_z_scores(article_id, email, values)
            self.redirect("/view-article?id=" + str(article_id))

# contribute page


class ContributionHandler(BaseHandler):
    def get(self):
        self.render_with_user_info('static/html/contribute.html')

# takes a file in JSON format and adds the articles to our database
# (called from the contribute page)


class BulkAddHandler(BaseHandler):
    # TODO: make JSON endpoint
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

# update a vote on a table tag


class TableVoteUpdateHandler(
        BaseHandler):  # TODO: make into a JSON API endpoint
    def post(self):
        tag_name = self.get_argument("tag_name")
        direction = self.get_argument("direction")
        table_num = self.get_argument("table_num")
        pmid = self.get_argument("id")
        column = self.get_argument("column")
        user = self.get_current_github_username()
        update_table_vote(tag_name, direction, table_num, pmid, column, user)
        self.redirect("/view-article?id=" + pmid)
