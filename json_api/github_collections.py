import hashlib
import os
from base64 import b64encode

import tornado
import tornado.web
import torngithub
from tornado.httputil import url_concat
from torngithub import json_encode

from base_handler import *
from search import *
from user_accounts import *

# BEGIN: read environment variables

if "github_client_id" not in os.environ:
    print("set your github_client_id env variable, and register your app at https://github.com/settings/developers")
    os.environ["github_client_id"] = "gh_client_id"
if "github_client_secret" not in os.environ:
    print("set your github_client_secret env variable, and register your app at https://github.com/settings/developers")
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
        # next is the redirect_uri
        redirect_uri = url_concat(self.request.protocol
                                  + "://" + self.request.host
                                  + "/oauth",
                                  {"next":
                                   self.get_argument('next', '/')})
        print(redirect_uri)

        # if we have a code, we have been authorized so we can log in
        if self.get_argument("code", False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=settings["github_client_id"],
                client_secret=settings["github_client_secret"],
                code=self.get_argument("code")
            )
            if user:
                self.set_secure_cookie("user", json_encode(user))
                # idempotent operation to make sure GitHub user is in our
                # database
                register_github_user(json_encode(user))
                api_key = str(user["id"])
                hasher = hashlib.sha1()
                hasher.update(api_key.encode('utf-8'))
                api_key = hasher.hexdigest()
                self.set_secure_cookie("api_key", api_key)
            else:
                self.clear_cookie("user")
            self.redirect(self.get_argument("next", "/"))
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
        self.redirect(self.get_argument("next", "/"))


def parse_link(link):
    linkmap = {}
    for s in link.split(","):
        s = s.strip()
        linkmap[s[-5:-1]] = s.split(";")[0].rstrip()[1:-1]
    return linkmap


def get_last_page_num(link):
    if not link:
        return 0
    linkmap = parse_link(link)
    matches = re.search(r"[?&]page=(\d+)", linkmap["last"])
    return int(matches.group(1))


@tornado.gen.coroutine
def get_my_repos(http_client, access_token):
    data = []
    first_page = yield torngithub.github_request(
        http_client, '/user/repos?page=1&per_page=100',
        access_token=access_token)
    # log.info(first_page.headers.get('Link', ''))
    data.extend(first_page.body)
    max_pages = get_last_page_num(first_page.headers.get('Link', ''))

    ress = yield [torngithub.github_request(
        http_client, '/user/repos?per_page=100&page=' + str(i),
        access_token=access_token) for i in range(2, max_pages + 1)]

    for res in ress:
        data.extend(res.body)

    raise tornado.gen.Return(data)


class ReposHandler(BaseHandler, torngithub.GithubMixin):
    """ TODO: We should update the database if there is a discrepency"""
    # @tornado.web.authenticated
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            return_list = self.get_argument("list")
        except tornado.web.MissingArgumentError:  # AK: This is hacky.
            return_list = False
        try:
            pmid = self.get_argument("pmid")
        except tornado.web.MissingArgumentError:  # AK: This is again hacky.
            pmid = False

        gh_user = self.__get_current_github_object__()
        if self.get_current_github_access_token():
            # get all repos for an authenticated user
            data = yield get_my_repos(self.get_auth_http_client(),
                                      self.get_current_github_access_token())
            repos = [d for d in data if d["name"].startswith(
                "brainspell-collection")]

            # TODO: Ideally this information would be store in the database
            # this is pretty hacky. I'm checking gathering info for each pmid in
            # each collection. If the user speficified a pmid in the REST call, then
            # check if the pmid exists in the collection

            for repo in repos:
                # this is the name w/out the brainspell-collection in it

                repo["pretty_name"] = repo["name"].replace(
                    "brainspell-collection-", "")

                # get file list content for each repo
                try:
                    content_data = yield torngithub.github_request(
                        self.get_auth_http_client(),
                        '/repos/{owner}/{repo}/contents/{path}'.format(owner=self.get_current_github_username(),
                                                                       repo=repo["name"],
                                                                       # path="{}.json".format(pmid)
                                                                       path=""
                                                                       ),
                        access_token=self.get_current_github_access_token(),
                        method="GET")

                    print(repo["contributors_url"])
                    contrib = yield torngithub.github_request(self.get_auth_http_client(),
                                                              repo["contributors_url"].replace("https://api.github.com", ""),
                                                              access_token=self.get_current_github_access_token(),
                                                              method="GET")
                    repo["contributors"] = contrib["body"]

                    # print(content_data)

                    content = content_data["body"]

                    # extract pmids from content body
                    pmids = [c["name"].replace(".json", "") for c in content]

                    # If we are looking for a certaim pmid, add a tag for if it
                    # exists in the collection
                    if pmid:
                        if pmid in pmids:
                            repo["in_collection"] = True
                        else:
                            repo["in_collection"] = False

                    # get article information from each pmid from the database
                    all_contents = [next(get_article(pmid)) for pmid in pmids]
                except BaseException:  # TODO This is hacky, Empty Repos break the code!
                    all_contents = []
                    repo["contributors"] = {}

                # Convert to a dict the info we want (so it can be JSON
                # serialized later)
                def article_content_dict(cont):
                    return dict(
                        title=cont.title,
                        reference=cont.reference,
                        pmid=cont.pmid)
                repo["contents"] = [
                    article_content_dict(cont) for cont in all_contents]

            # if we want to return a JSON instead or a page render
            if return_list:
                self.write(json_encode(repos))
            else:
                self.render_with_user_info("static/html/github-account.html", {
                    "info": repos
                })

        # if you're not authorized, redirect to oauth
        else:
            self.redirect("/oauth?next=/repos")


class NewRepoHandler(BaseHandler, torngithub.GithubMixin):
    """ Create a new GitHub repo for a collection. """

    # TODO Again update the database
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        starttime = time.time()
        name = self.get_argument("name")
        desc = self.get_argument("description")
        if not name:
            self.write("")
        else:
            # Update database with new Collection

            new_repo(name, self.get_current_github_username())
            body = {
                "name": "brainspell-collection-{}".format(name),
                "description": desc,
                "homepage": "https://brainspell-neo.herokuapp.com",
                "private": False,
                "has_issues": True,
                "has_projects": True,
                "has_wiki": True
            }
            ress = yield [torngithub.github_request(
                self.get_auth_http_client(), '/user/repos',
                access_token=self.get_current_github_access_token(),
                method="POST",
                body=body)]
            data = []
            for res in ress:
                data.extend(res.body)

            endtime = time.time()
            # print(data)
            return self.redirect("/repos")


class NewFileHandler(BaseHandler, torngithub.GithubMixin):
    # Adds a json file to github repository
    # Add to database as well
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        starttime = time.time()
        collection = self.get_argument("collection")
        pmid = self.get_argument("pmid")
        print("Collection is {0} and PMID is {1}".format(collection, pmid))
        print(
            "Type of collection is {0} and type of PMID is {1}".format(
                type(collection),
                type(pmid)))
        article = list(get_article(pmid))[0]
        entry = {"pmid": pmid,
                 "title": article.title,
                 "reference": article.reference,
                 "doi": article.doi,
                 "notes": "Here are my notes on this article"}
        content = b64encode(json_encode(entry).encode("utf-8")).decode('utf-8')

        name = collection

        coll_indicator = new_repo(name, self.get_current_github_username())

        if coll_indicator:
            print("Creating collection: " + name)
            body = {
                "name": name,
                "description": "",
                "homepage": "https://brainspell-neo.herokuapp.com",
                "private": False,
                "has_issues": True,
                "has_projects": True,
                "has_wiki": True
            }
            ress = yield [torngithub.github_request(
                self.get_auth_http_client(), '/user/repos',
                access_token=self.get_current_github_access_token(),
                method="POST",
                body=body)]
            data = []
            for res in ress:
                data.extend(res.body)
            print("Created collection")

        add_to_repo(collection, pmid, self.get_current_github_username())
        body = {
            "message": "adding {} to collection".format(pmid),
            "content": content
        }
        ress = yield [torngithub.github_request(
            self.get_auth_http_client(),
            '/repos/{owner}/{repo}/contents/{path}'.format(owner=self.get_current_github_username(),
                                                           repo=collection,
                                                           path="{}.json".format(pmid)),
            access_token=self.get_current_github_access_token(),
            method="PUT",
            body=body)]
        data = []
        for res in ress:
            data.extend(res.body)

        endtime = time.time()


class DeleteFileHandler(BaseHandler, torngithub.GithubMixin):
    # Deletes a JSON file from the User Repo
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        starttime = time.time()
        collection = self.get_argument("collection")
        pmid = self.get_argument("pmid")
        entry = {"pmid": pmid,
                 "notes": "Here are my notes on this article"}
        content = b64encode(json_encode(entry).encode("utf=8"))
        gh_user = self.__get_current_github_object__()

        remove_from_repo(collection, pmid, self.get_current_github_username())

        body = {
            "message": "deleting {} to collection".format(pmid),
        }

        sha_data = yield [torngithub.github_request(
            self.get_auth_http_client(),
            '/repos/{owner}/{repo}/contents/{path}'.format(owner=self.get_current_github_username(),
                                                           repo=collection,
                                                           path="{}.json".format(pmid)),
            access_token=self.get_current_github_access_token(),
            method="GET")]

        sha = [s["body"]["sha"] for s in sha_data][0]

        ress = yield [torngithub.github_request(
            self.get_auth_http_client(),
            '/repos/{owner}/{repo}/contents/{path}'.format(owner=self.get_current_github_username(),
                                                           repo=collection,
                                                           path="{}.json".format(pmid)),
            access_token=self.get_current_github_access_token(),
            method="DELETE",
            body={"sha": sha, "message": "removing {} from collection".format(pmid)})]


"""
 class BulkNewFileHandler(BaseHandler, torngithub.GithubMixin):
     @tornado.web.asynchronous
     @tornado.gen.coroutine
     def post(self):
         startime = time.time()
         collection = self.get_argument("collection")
         pmids = self.get_argument("pmids")
         pmids = eval(pmids)
         user_info = self.__get_current_github_object__()["login"]
         if collection in next(User.select().where(User.username == user_info).execute()).collections: #If collection exists
             collection = "brainspell-collection-" + collection
             for pmid in pmids:
                 pmid = eval(pmid)
                 article = list(get_article(pmid))[0]
                 entry = {"pmid": pmid,
                         "title": article.title,
                         "reference": article.reference,
                         "doi": article.doi,
                          "notes": "Here are my notes on this article"}
                 content = b64encode(json_encode(entry).encode("utf-8")).decode('utf-8')
                 gh_user = self.__get_current_github_object__()
                 add_to_repo(collection,pmid,self.get_current_github_username())
                 body = {
                     "message": "adding {} to collection".format(pmid),
                     "content": content
                 }
                 ress = yield [
                     torngithub.github_request(
                         self.get_auth_http_client(),
                         '/repos/{owner}/{repo}/contents/{path}'.format(owner=self.get_current_github_username(),
                                                                        repo=collection,
                                                                        path="{}.json".format(pmid)),
                         access_token=self.get_current_github_access_token(),
                         method="PUT",
                         body=body
                     )
                 ]
                 data = []
                 for res in ress:
                     data.extend(res.body)
                 endtime = time.time()
         else:
             print("Your collection doesn't exist")
             return False #TODO: Tell user the collection doesn't exist
"""
