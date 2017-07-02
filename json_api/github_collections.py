"""
User account handlers, which are in a different file because
they have unique dependencies. These handlers make requests to the
GitHub API.
"""

import hashlib
import os
from base64 import b64encode

import tornado
import tornado.gen
import tornado.web
import torngithub
from tornado.concurrent import run_on_executor
from tornado.httputil import url_concat
from torngithub import json_encode

from base_handler import *
from search_helpers import *
from user_account_helpers import *

# BEGIN: read environment variables

if "github_client_id" not in os.environ:
    print("Set your github_client_id environment variable, and register your app at https://github.com/settings/developers")
    os.environ["github_client_id"] = "gh_client_id"
if "github_client_secret" not in os.environ:
    print("Set your github_client_secret environment variable, and register your app at https://github.com/settings/developers")
    os.environ["github_client_secret"] = "github_client_secret"

settings = {
    "github_client_id": os.environ["github_client_id"],
    "github_client_secret": os.environ["github_client_secret"]
}

# BEGIN: GitHub repo handlers


class GithubLoginHandler(tornado.web.RequestHandler, torngithub.GithubMixin):
    """ Handle GitHub OAuth. """

    @tornado.gen.coroutine
    def get(self):
        # Heroku does not accurately give self.request.protocol
        if self.request.host[0:9] == "localhost":
            protocol = "http"
        else:
            protocol = "https"

        redirect_uri = url_concat(protocol
                                  + "://" + self.request.host
                                  + "/oauth",
                                  {"redirect_uri":
                                   self.get_argument('redirect_uri', '/')})

        # if we have a code, we have been authorized so we can log in
        if self.get_argument("code", False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=settings["github_client_id"],
                client_secret=settings["github_client_secret"],
                code=self.get_argument("code")
            )

            # if the user is valid
            if user:
                self.set_secure_cookie("user", json_encode(user))
                # idempotent operation to make sure GitHub user is in our
                # database
                register_github_user(json_encode(user))
                # generate a Brainspell API key
                hasher = hashlib.sha1()
                hasher.update(str(user["id"]).encode('utf-8'))
                api_key = hasher.hexdigest()
                self.set_secure_cookie("api_key", api_key)
            else:
                self.clear_cookie("user")
            self.redirect(self.get_argument("redirect_uri", "/"))
            return

        # otherwise we need to request an authorization code
        yield self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=settings["github_client_id"],
            extra_params={"scope": "repo"})


class GithubLogoutHandler(BaseHandler):
    """ Clear login cookies. """

    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("redirect_uri", "/"))


def get_last_page_num(link):
    """ Extract the number of pages from the GitHub result. """

    if not link:
        return 0
    linkmap = {}
    for s in link.split(","):
        s = s.strip()
        linkmap[s[-5:-1]] = s.split(";")[0].rstrip()[1:-1]
    matches = re.search(r"[?&]page=(\d+)", linkmap["last"])
    return int(matches.group(1))


@tornado.gen.coroutine
def get_user_repos(http_client, access_token):
    """ Get a user's repos. """

    data = []

    # get the results in groups of 100
    first_page = yield torngithub.github_request(
        http_client, '/user/repos?page=1&per_page=100',
        access_token=access_token)
    data.extend(first_page.body)

    # get the number of pages (repos // 100 + 1)
    max_pages = get_last_page_num(first_page.headers.get('Link', ''))

    repos_list = yield [torngithub.github_request(
        http_client, '/user/repos?per_page=100&page=' + str(i),
        access_token=access_token) for i in range(2, max_pages + 1)]

    for repo in repos_list:
        data.extend(res.body)

    raise tornado.gen.Return(data)


class CollectionsEndpointHandler(BaseHandler, torngithub.GithubMixin):
    """ Return a list of the user's collections. """

    parameters = {
        "pmid": {
            "type": str,
            "default": ""
        },
        "github_access_token": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PUSH_API
    asynchronous = True

    @tornado.gen.coroutine
    def process(self, response, args):
        collections_list = []

        # get all repos for an authenticated user
        data = yield get_user_repos(self.get_auth_http_client(),
                                    self.get_current_github_access_token())
        repos = [d for d in data if d["name"].startswith(
            "brainspell-collection")]

        # TODO: ideally this information would be stored in the database

        # for each repo
        for repo_contents in repos:
            repo = {
                # take the "brainspell-collection" off of the name
                "name": repo_contents["name"].replace("brainspell-collection-", ""),
                "description": repo_contents["description"]
            }

            # get the contributor info for this collection
            contributor_info = yield torngithub.github_request(self.get_auth_http_client(),
                                                               repo_contents["contributors_url"].replace("https://api.github.com", ""),
                                                               access_token=self.get_current_github_access_token(),
                                                               method="GET")
            repo["contributors"] = []
            if contributor_info["body"]:
                repo["contributors"] = contributor_info["body"]
            # get the PMIDs in the collection
            try:
                content_data = yield torngithub.github_request(
                    self.get_auth_http_client(),
                    '/repos/{owner}/{repo}/contents/{path}'.format(owner=self.get_current_github_username(),
                                                                   repo=repo_contents["name"],
                                                                   path=""
                                                                   ),
                    access_token=self.get_current_github_access_token(),
                    method="GET")
                content = content_data["body"]

                # extract PMIDs from content body
                pmids = [c["name"].replace(".json", "") for c in content]

                # if we are looking for a certain PMID, add a tag for if it
                # exists in the collection
                if pmid:
                    if pmid in pmids:
                        repo["in_collection"] = True
                    else:
                        repo["in_collection"] = False

                # convert PeeWee article object to dict
                def parse_article_object(article_object):
                    return {
                        "title": article_object.title,
                        "reference": article_object.reference,
                        "pmid": article_object.pmid
                    }

                # get article information from each pmid from the database
                repo["contents"] = [parse_article_object(
                    next(get_article_object(pmid))) for pmid in pmids]
            except BaseException:
                # empty repo; not a problem
                repo["contents"] = []
            collections_list.append(repo)
        response["collections"] = collections_list
        self.finish_async(response)


class CreateCollectionEndpointHandler(BaseHandler, torngithub.GithubMixin):
    """
    Create a new GitHub repo for a collection.

    Called from the /collections page.
    """

    parameters = {
        "name": {
            "type": str
        },
        "description": {
            "type": str
        },
        "github_access_token": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PUSH_API
    asynchronous = True

    @tornado.gen.coroutine
    def create_collection_on_github(
            self,
            name,
            description,
            access_token,
            callback=None):
        body = {
            "name": "brainspell-collection-{}".format(name),
            "description": description,
            "homepage": "https://brainspell-neo.herokuapp.com",
            "private": False,
            "has_issues": True,
            "has_projects": True,
            "has_wiki": True
        }

        # not blocking because torngithub is asynchronous
        ress = yield [torngithub.github_request(
            self.get_auth_http_client(), '/user/repos', callback,
            access_token=access_token,
            method="POST",
            body=body)]

        return ress

    @tornado.gen.coroutine
    def process(self, response, args):
        name = args["name"]
        # update database with new collection
        if add_collection_to_brainspell_database(name, args["key"]):
            # if the collection doesn't already exist, then make the GitHub
            # request
            self.create_collection_on_github(
                name, args["description"], args["github_access_token"])
            self.finish_async(response)

        else:
            response["success"] = 0
            response["description"] = "That collection already exists."
            self.finish_async(response)


class AddToCollectionEndpointHandler(BaseHandler, torngithub.GithubMixin):
    """
    Add an article to a collection.

    Add to the GitHub repo, and to Brainspell's database.
    """

    parameters = {
        "pmid": {
            "type": str
        },
        "name": {
            "type": str,
            "description": "The name of the collection to add this article to"
        },
        "github_access_token": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PUSH_API
    asynchronous = True

    @tornado.gen.coroutine
    def process(self, response, args):
        name = args["name"]
        pmid = args["pmid"]

        article = list(get_article_object(pmid))[0]

        # create the entry to add to the GitHub repo
        entry = {"pmid": pmid,
                 "title": article.title,
                 "reference": article.reference,
                 "doi": article.doi,
                 "notes": "Here are my notes on this article."}
        entry_encoded = b64encode(
            json_encode(entry).encode("utf-8")).decode('utf-8')

        @tornado.gen.coroutine
        def callback_function(github_response=None):
            # check if the article is already in this collection
            if add_article_to_brainspell_database_collection(
                    name, pmid, args["key"]):
                body = {
                    "message": "adding {} to collection".format(pmid),
                    "content": entry_encoded
                }
                try:
                    github_username = get_github_username_from_api_key(
                        args["key"])
                    github_collection_name = "brainspell-collection-{}".format(
                        name)
                    ress = yield [torngithub.github_request(
                        self.get_auth_http_client(),
                        '/repos/{owner}/{repo}/contents/{path}'.format(owner=github_username,
                                                                       repo=github_collection_name,
                                                                       path="{}.json".format(pmid)),
                        access_token=args["github_access_token"],
                        method="PUT",
                        body=body)]
                except Exception as e:  # if you want to debug further
                    response["success"] = 0
                    # catch all GitHub request errors
                    print(e)
                    response["description"] = "Most likely, that article already exists in this collection."
            else:
                response["success"] = 0
                response["description"] = "That article already exists in that collection."
            self.finish_async(response)

        # if the collection doesn't exist, asynchronously create it
        if add_collection_to_brainspell_database(name, args["key"]):
            print("Creating collection: " + name)
            CreateCollectionEndpointHandler.create_collection_on_github(
                self, name, "", args["github_access_token"], callback_function)
        else:
            callback_function()


class DeleteFromCollectionEndpointHandler(BaseHandler, torngithub.GithubMixin):
    """
    Delete an article from a collection.

    Delete from the GitHub repo, and from Brainspell's database.
    """

    parameters = {
        "pmid": {
            "type": str
        },
        "name": {
            "type": str,
            "description": "The name of the collection to delete this article from"
        },
        "github_access_token": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PUSH_API
    asynchronous = True

    @tornado.gen.coroutine
    def process(self, response, args):
        collection = args["name"]
        pmid = args["pmid"]

        if remove_article_from_brainspell_database_collection(
                collection, pmid, args["key"]):
            github_username = get_github_username_from_api_key(args["key"])
            github_collection_name = "brainspell-collection-{}".format(
                collection)
            try:
                # get SHA data for deletion
                sha_data = yield [torngithub.github_request(
                    self.get_auth_http_client(),
                    '/repos/{owner}/{repo}/contents/{path}'.format(owner=github_username,
                                                                   repo=github_collection_name,
                                                                   path="{}.json".format(pmid)),
                    access_token=args["github_access_token"],
                    method="GET")]
                sha = [s["body"]["sha"] for s in sha_data][0]

                # make deletion request
                ress = yield [torngithub.github_request(
                    self.get_auth_http_client(),
                    '/repos/{owner}/{repo}/contents/{path}'.format(owner=github_username,
                                                                   repo=github_collection_name,
                                                                   path="{}.json".format(pmid)),
                    access_token=args["github_access_token"],
                    method="DELETE",
                    body={"sha": sha, "message": "removing {} from collection".format(pmid)})]
            except Exception as e:
                print(e)
                response["success"] = 0
                response["description"] = "There was some failure in communicating with GitHub. That article was possibly not in the collection."
        else:
            response["success"] = 0
            response["description"] = "That article doesn't exist in that collection."

        self.finish_async(response)
