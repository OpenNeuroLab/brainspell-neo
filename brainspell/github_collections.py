"""
User account handlers, which are in a different file because
they have unique dependencies. These handlers make requests to the
GitHub API.
"""

import hashlib
import os
from base64 import b64decode, b64encode

import tornado
import tornado.gen
import tornado.web
import torngithub
from tornado.concurrent import run_on_executor
from tornado.httputil import url_concat
from torngithub import json_decode, json_encode

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

    route = "oauth"
    settings_key_id = "github_client_id"
    settings_key_secret = "github_client_secret"

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
                client_id=settings[self.settings_key_id],
                client_secret=settings[self.settings_key_secret],
                code=self.get_argument("code")
            )

            # if the user is valid
            if user:
                self.set_secure_cookie("user", json_encode(user))
                # idempotent operation to make sure GitHub user is in our
                # database
                register_github_user(user)
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
            client_id=settings[self.settings_key_id],
            extra_params={"scope": "repo"})


class GithubLogoutHandler(BaseHandler):
    """ Clear login cookies. """

    route = "logout"

    def get(self):
        self.clear_cookie("user")
        self.clear_cookie("api_key")
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
        data.extend(repo.body)

    raise tornado.gen.Return(data)


class CollectionsEndpointHandler(BaseHandler, torngithub.GithubMixin):
    """ Return a list of the user's collections, with contributor information. """

    parameters = {
        "pmid": {
            "type": str,
            "default": 0
        },
        "github_access_token": {
            "type": str
        },
        "force_github_refresh": {
            "type": int,
            "default": 0,
            "description": "Set this to 1 to force Brainspell to sync its local database with GitHub. There should be a button for this on the web interface."
        }
    }

    endpoint_type = Endpoint.PUSH_API
    asynchronous = True

    @tornado.gen.coroutine
    def process(self, response, args):
        collections_list = []

        # get all repos for an authenticated user using GitHub
        # need to use GitHub, because not storing "contributors_url" in
        # Brainspell's database
        data = yield get_user_repos(self.get_auth_http_client(), args["github_access_token"])
        repos = [d for d in data if d["name"].startswith(
            "brainspell-collection-")]

        if args["force_github_refresh"] == 1:
            remove_all_brainspell_database_collections(args["key"])

        # get all repos using the Brainspell database
        brainspell_cache = get_brainspell_collections_from_api_key(args["key"])

        # for each repo
        for repo_contents in repos:
            # guaranteed that the name starts with "brainspell-collection"
            # (from above)
            collection_name = repo_contents["name"][len(
                "brainspell-collection-"):]
            repo = {
                # take the "brainspell-collection" off of the name
                "name": collection_name,
                "description": repo_contents["description"]
            }

            # get the contributor info for this collection
            contributor_info = yield torngithub.github_request(self.get_auth_http_client(),
                                                               repo_contents["contributors_url"].replace("https://api.github.com", ""),
                                                               access_token=args["github_access_token"],
                                                               method="GET")
            repo["contributors"] = []
            if contributor_info["body"]:
                repo["contributors"] = contributor_info["body"]

            # get the PMIDs in the collection

            description = repo_contents["description"]
            valid_collection = True

            # if there's a new GitHub collection added to the user's profile,
            # then add it
            if collection_name not in brainspell_cache:
                try:
                    # fetch the PMIDs from GitHub
                    github_username = get_github_username_from_api_key(
                        args["key"])
                    content_data = yield torngithub.github_request(
                        self.get_auth_http_client(),
                        '/repos/{owner}/{repo}/contents/{path}'.format(owner=github_username,
                                                                       repo=repo_contents["name"],
                                                                       path="manifest.json"),
                        access_token=args["github_access_token"],
                        method="GET")
                    content = content_data["body"]["content"]
                    # parse the manifest.json file for the collection
                    collection_contents = json_decode(
                        b64decode(content.encode('utf-8')).decode('utf-8'))
                    pmids = [c["pmid"] for c in collection_contents]

                    add_collection_to_brainspell_database(
                        collection_name, description, args["key"], False)
                    brainspell_cache[collection_name] = {
                        "description": description,
                        "pmids": pmids
                    }
                    if len(pmids) != 0:
                        # if PMIDs were fetched from GitHub
                        bulk_add_articles_to_brainspell_database_collection(
                            collection_name, pmids, args["key"], False)

                except BaseException:
                    # some error occurred with GitHub
                    # there was potentially no manifest file
                    valid_collection = False

            if valid_collection:
                # accounts for malformed collections, and excludes them
                pmids = brainspell_cache[collection_name]["pmids"]

                # determine if the pmid (if given) is in this collection
                repo["in_collection"] = any(
                    [str(pmid) == args["pmid"] for pmid in pmids])

                # convert PeeWee article object to dict
                def parse_article_object(article_object):
                    return {
                        "title": article_object.title,
                        "reference": article_object.reference,
                        "pmid": article_object.pmid
                    }

                # get article information from each pmid from the database
                repo["contents"] = [parse_article_object(
                    next(get_article_object(p))) for p in pmids]

                collections_list.append(repo)
        response["collections"] = collections_list
        self.finish_async(response)


class CollectionsFromBrainspellEndpointHandler(
        BaseHandler, torngithub.GithubMixin):
    """
    Return a list of the user's collections from the Brainspell database.

    Called from /view-article pages.
    """

    parameters = {
        "pmid": {
            "type": str,
            "default": 0
        }
    }

    endpoint_type = Endpoint.PUSH_API

    def process(self, response, args):

        collections_list = []

        user_collections = get_brainspell_collections_from_api_key(args["key"])

        for c in user_collections:
            repo = {}

            repo["name"] = c
            pmids = user_collections[c]["pmids"]

            # determine if the pmid is in this collection
            repo["in_collection"] = any(
                [str(pmid) == args["pmid"] for pmid in pmids])

            collections_list.append(repo)

        response["collections"] = collections_list

        return response


class CreateCollectionEndpointHandler(BaseHandler, torngithub.GithubMixin):
    """
    Create a new GitHub repo for a collection.

    Called from the /collections page.
    """

    parameters = {
        "name": {
            "type": str,
            "description": "The name of the new collection; this is the name that the user will see."
        },
        "description": {
            "type": str,
            "default": "",
            "description": "An optional description for this collection."
        },
        "github_access_token": {
            "type": str
        }
    }

    endpoint_type = Endpoint.PUSH_API
    asynchronous = True

    @tornado.gen.coroutine
    def __create_repo_on_github__(
            self,
            name,
            description,
            access_token,
            callback=None):

        github_collection_name = "brainspell-collection-{}".format(
            name)

        create_repo_body = {
            "name": github_collection_name,
            "description": description,
            "homepage": "https://brainspell-neo.herokuapp.com",
            "private": False,
            "has_issues": True,
            "has_projects": True,
            "has_wiki": True
        }

        # not blocking because torngithub is asynchronous
        create_repo_ress = yield [torngithub.github_request(
            self.get_auth_http_client(), '/user/repos', callback,
            access_token=access_token,
            method="POST",
            body=create_repo_body)]

        return create_repo_ress

    @tornado.gen.coroutine
    def __create_manifest_file__(
            self,
            name,
            access_token,
            github_username,
            callback=None):

        github_collection_name = "brainspell-collection-{}".format(
            name)

        initial_manifest_contents = []
        manifest_contents_encoded = b64encode(
            json_encode(initial_manifest_contents).encode("utf-8")).decode('utf-8')

        create_manifest_body = {
            "message": "creating manifest.json file",
            "content": manifest_contents_encoded
        }

        create_manifest_ress = yield [torngithub.github_request(
            self.get_auth_http_client(),
            '/repos/{owner}/{repo}/contents/{path}'.format(owner=github_username,
                                                           repo=github_collection_name,
                                                           path="manifest.json"),
            callback=callback,
            access_token=access_token,
            method="PUT",
            body=create_manifest_body)]

        return create_manifest_ress

    @tornado.gen.coroutine
    def create_collection_on_github(
            self,
            name,
            description,
            access_token,
            github_username,
            callback=None):
        def create_manifest_file(github_response=None):
            # once the collection repo is created, make the manifest.json file
            self.__create_manifest_file__(
                name, access_token, github_username, callback=callback)

        self.__create_repo_on_github__(
            name, description, access_token, callback=create_manifest_file)

    @tornado.gen.coroutine
    def process(self, response, args):
        name = args["name"]
        description = args["description"]
        # update database with new collection
        if add_collection_to_brainspell_database(
                name, description, args["key"]):
            # if the collection doesn't already exist, then make the GitHub
            # request

            def completed_manifest(github_response=None):
                # and actually create the Brainspell collection if the requests
                # succeed
                add_collection_to_brainspell_database(
                    name, description, args["key"], False)
                self.finish_async(response)

            github_username = get_github_username_from_api_key(args["key"])
            self.create_collection_on_github(
                name,
                description,
                args["github_access_token"],
                github_username,
                callback=completed_manifest)

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
            "description": "The name of the collection to add this article to, without the brainspell-collection at the beginning"
        },
        "github_access_token": {
            "type": str
        },
        "bulk_add": {
            "type": int,
            "default": 0,
            "description": "If set to one, then PMID will be treated as a JSON array. Send multiple PMIDs at once, and they'll all be added."
        }
    }

    endpoint_type = Endpoint.PUSH_API
    asynchronous = True

    @tornado.gen.coroutine
    def process(self, response, args):
        name = args["name"]

        @tornado.gen.coroutine
        def callback_function(github_response=None):
            # check if the article is already in this collection
            # doesn't matter if we're bulk adding
            if args["bulk_add"] == 1 or add_article_to_brainspell_database_collection(
                    name, args["pmid"], args["key"]):
                pmid = args["pmid"]
                # idempotent operation to create the Brainspell collection
                # if it doesn't already exist (guaranteed that it exists on
                # GitHub)
                add_collection_to_brainspell_database(
                    name, "None", args["key"], False)

                # make a single PMID into a list so we can treat it the same
                # way
                if args["bulk_add"] == 0:
                    pmid = "[" + pmid + "]"
                pmid_list = json_decode(pmid)

                # add all of the PMIDs to GitHub, then insert to Brainspell

                github_username = get_github_username_from_api_key(
                    args["key"])
                github_collection_name = "brainspell-collection-{}".format(
                    name)
                try:
                    content_data = yield torngithub.github_request(
                        self.get_auth_http_client(),
                        '/repos/{owner}/{repo}/contents/{path}'.format(owner=github_username,
                                                                       repo=github_collection_name,
                                                                       path="manifest.json"),
                        access_token=args["github_access_token"],
                        method="GET")
                except BaseException as e:
                    response["success"] = 0
                    response["description"] = "The request failed. Make sure that the manifest.json file exists in your repository."
                    response["exception"] = str(e)
                    self.finish_async(response)
                content = content_data["body"]["content"]
                # get the SHA so we can update this file
                manifest_sha = content_data["body"]["sha"]
                # parse the manifest.json file for the collection
                collection_contents = json_decode(
                    b64decode(content.encode('utf-8')).decode('utf-8'))
                article_set = set([c["pmid"] for c in collection_contents])

                for p in pmid_list:
                    if p not in article_set:
                        # create the entry to add to the GitHub repo
                        article = list(get_article_object(p))[0]
                        article_entry = {
                            "pmid": p,
                            "title": article.title,
                            "reference": article.reference,
                            "doi": article.doi,
                            "notes": "Here are my notes on this article."
                        }
                        collection_contents.append(article_entry)
                        article_set.add(p)

                manifest_contents_encoded = b64encode(
                    json_encode(collection_contents).encode("utf-8")).decode('utf-8')

                update_manifest_body = {
                    "message": "creating manifest.json file",
                    "content": manifest_contents_encoded,
                    "sha": manifest_sha
                }

                try:
                    update_manifest_ress = yield [torngithub.github_request(
                        self.get_auth_http_client(),
                        '/repos/{owner}/{repo}/contents/{path}'.format(owner=github_username,
                                                                       repo=github_collection_name,
                                                                       path="manifest.json"),
                        access_token=args["github_access_token"],
                        method="PUT",
                        body=update_manifest_body)]
                except BaseException as e:
                    response["success"] = 0
                    response["description"] = "The request failed. Make sure that you have write permissions for the manifest.json file in your repository."
                    response["exception"] = str(e)

                # actually add the article(s) if the request succeeds
                bulk_add_articles_to_brainspell_database_collection(
                    name, pmid_list, args["key"], False)
            else:
                response["success"] = 0
                response["description"] = "That article already exists in that collection."
            self.finish_async(response)

        # if the collection doesn't exist, asynchronously create it
        if add_collection_to_brainspell_database(name, "None", args["key"]):
            print("Creating collection: " + name)
            github_username = get_github_username_from_api_key(args["key"])
            CreateCollectionEndpointHandler.create_collection_on_github(
                self,
                name,
                "",
                args["github_access_token"],
                github_username,
                callback=callback_function)
        else:
            callback_function()


class RemoveFromCollectionEndpointHandler(BaseHandler, torngithub.GithubMixin):
    """
    Remove an article from a collection.

    Remove from the GitHub repo, and from Brainspell's database.
    """

    parameters = {
        "pmid": {
            "type": str
        },
        "name": {
            "type": str,
            "description": "The name of the collection to remove this article from, without the brainspell-collection at the beginning"
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
                content_data = yield torngithub.github_request(
                    self.get_auth_http_client(),
                    '/repos/{owner}/{repo}/contents/{path}'.format(owner=github_username,
                                                                   repo=github_collection_name,
                                                                   path="manifest.json"),
                    access_token=args["github_access_token"],
                    method="GET")
                content = content_data["body"]["content"]
                # get the SHA so we can update this file
                manifest_sha = content_data["body"]["sha"]
                # parse the manifest.json file for the collection
                collection_contents = json_decode(
                    b64decode(content.encode('utf-8')).decode('utf-8'))

                collection_contents = [
                    c for c in collection_contents if str(
                        c["pmid"]) != pmid]

                manifest_contents_encoded = b64encode(
                    json_encode(collection_contents).encode("utf-8")).decode('utf-8')

                update_manifest_body = {
                    "message": "creating manifest.json file",
                    "content": manifest_contents_encoded,
                    "sha": manifest_sha
                }

                update_manifest_ress = yield [torngithub.github_request(
                    self.get_auth_http_client(),
                    '/repos/{owner}/{repo}/contents/{path}'.format(owner=github_username,
                                                                   repo=github_collection_name,
                                                                   path="manifest.json"),
                    access_token=args["github_access_token"],
                    method="PUT",
                    body=update_manifest_body)]
            except Exception as e:
                print(e)
                response["success"] = 0
                response["description"] = "There was some failure in communicating with GitHub."
            finally:
                if response["success"] != 0:
                    # only remove from Brainspell collection if the GitHub
                    # operation succeeded
                    remove_article_from_brainspell_database_collection(
                        collection, pmid, args["key"], False)
        else:
            response["success"] = 0
            response["description"] = "That article doesn't exist in that collection."

        self.finish_async(response)
