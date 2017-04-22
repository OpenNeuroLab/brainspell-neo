import urllib
import tornado.httpserver
import tornado.ioloop
import tornado.web
import os
import json
import peewee
import tornado
import psycopg2
import tornado.escape
from models import *
import subprocess
import hashlib
import torngithub
from torngithub import json_encode, json_decode
from tornado.httputil import url_concat
from base64 import b64encode
from helper_functions import *
import simplejson

# adds function to self
class BaseHandler(tornado.web.RequestHandler):
    def get_current_email(self):  # TODO: add password checking (currently not actually logged in)
        value = self.get_secure_cookie("email")
        if value and self.is_logged_in():
            return value
        return ""

    def get_current_user(self):
        if self.is_logged_in():
            for user in get_user(self.get_current_email()):
                return user.username
        return ""

    def get_current_github_user(self):
        user_json = self.get_secure_cookie("user")
        if not user_json:
            return {"name": None, "avatar_url": None, "access_token":None}
        else:
            try:
                return json_decode(user_json)
            except simplejson.scanner.JSONDecodeError:
                return {"name": None, "avatar_url": None, "access_token":None}

    def get_current_password(self):
        return self.get_secure_cookie("password")

    def is_logged_in(self):
        return user_login(self.get_secure_cookie("email"), self.get_current_password())


# front page
class MainHandler(BaseHandler):
    def get(self):
        email = self.get_current_email()
        gh_user = self.get_current_github_user()
        try:  # handle failures in bulk_add
            submitted = int(self.get_argument("success", 0))
        except:
            submitted = 0
        try:
            failure = int(self.get_argument("failure", 0))
        except:
            failure = 0
        try:  # handle registration
            registered = int(self.get_argument("registered", 0))
        except:
            registered = 0
        self.render("static/html/index.html", title=email,
                    github_user=gh_user["name"], github_avatar=gh_user["avatar_url"],
                    queries=Articles.select().wrapped_count(), success=submitted,
                    failure=failure, registered=registered, pw=self.get_current_password())


# login page
class LoginHandler(BaseHandler):
    def get(self):
        self.render("static/html/login.html", message="None", title="", failure=0)

    def post(self):
        email = self.get_argument("email")
        password = self.get_argument("password").encode("utf-8")
        hasher=hashlib.sha1()
        hasher.update(password)
        password = hasher.hexdigest()[:52]
        if user_login(email, password):
            self.set_secure_cookie("email", email)
            self.set_secure_cookie("password", password)
            self.redirect("/")
        else:
            self.render("static/html/login.html", message="Invalid", title="", failure=1)


# log out the user
class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("email")
        self.clear_cookie("password")
        self.redirect("/")


# registration page
class RegisterHandler(BaseHandler):
    def get(self):
        self.render("static/html/register.html", title="", failure=0)

    def post(self):
        username = self.get_body_argument("name").encode('utf-8')
        email = self.get_body_argument("email").encode('utf-8')
        password = self.get_body_argument("password").encode('utf-8')
        if register_user(username, email, password):
            self.set_secure_cookie("email", email)
            hasher=hashlib.sha1()
            hasher.update(password)
            password = hasher.hexdigest()[:52]
            self.set_secure_cookie("password", password)
            self.redirect("/?registered=1")
        else:
            self.render("static/html/register.html", title="", failure=1)


# search page
class SearchHandler(BaseHandler):
    def get(self):
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        req = self.get_query_argument("req", "t")
        email = self.get_current_email()
        gh_user = self.get_current_github_user()
        self.render("static/html/search.html", query=q, start=start,
                    title=email, req=req,
                    github_user=gh_user["name"],
                    github_avatar=gh_user["avatar_url"])


# API endpoint to fetch PubMed and Neurosynth data using a user specified PMID, and add the article to our database
class AddArticleEndpointHandler(BaseHandler):
    def get(self):
        pmid = self.get_query_argument("pmid", "")
        api_key = self.get_query_argument("key", "")
        response = {}
        if valid_api_key(api_key):
            x = getArticleData(pmid)
            request = Articles.insert(abstract=x["abstract"], doi=x["DOI"], authors=x["authors"],
                                      experiments=x["coordinates"], title=x["title"])
            request.execute()
            response = {"success": 1}
        else:
            response = {"success": 0}
        self.write(json.dumps(response))

class DeleteRowEndpointHandler(BaseHandler):
    def get(self):
        api_key = self.get_query_argument("key", "")
        if valid_api_key(api_key):
            pmid = self.get_query_argument("pmid", "")
            exp = self.get_query_argument("experiment", "")
            row = self.get_query_argument("row", "")
            print(pmid)
            delete_row(pmid, exp, row)
        self.write(json.dumps({"success": "1"}))

class SplitTableEndpointHandler(BaseHandler):
    def get(self):
        api_key = self.get_query_argument("key", "")
        if valid_api_key(api_key):
            pmid = self.get_query_argument("pmid", "")
            exp = self.get_query_argument("experiment", "")
            row = self.get_query_argument("row", "")
            split_table(pmid, exp, row)
        self.write(json.dumps({"success": "1"}))

class AddTableTextHandler(BaseHandler):
    def post(self):
        pmid = self.get_argument("pmid", "")
        vals = self.get_argument("values", "")
        if self.is_logged_in():
            add_table_text(pmid, vals)
        self.redirect("/view-article?id=" + pmid)

class FlagTableEndpointHandler(BaseHandler):
    def get(self):
        api_key = self.get_query_argument("key", "")
        if valid_api_key(api_key):
            pmid = self.get_query_argument("pmid", "")
            exp = int(self.get_query_argument("experiment", ""))
            flag_table(pmid, exp)
        self.write(json.dumps({"success": "1"}))

# view-article page
class ArticleHandler(BaseHandler):
    def get(self):
        articleId = -1
        try:
            articleId = self.get_query_argument("id")
        except:
            self.redirect("/")  # id wasn't passed; redirect to home page
        gh_user = self.get_current_github_user()
        self.render("static/html/view-article.html", id=articleId,
                    github_user=gh_user["name"], github_avatar=gh_user["avatar_url"],
                    title=self.get_current_email(), key=self.get_current_password())

    def post(self):  # TODO: maybe make its own endpoint (probably more appropriate than overloading this one)
        id = self.get_body_argument('id')
        email = self.get_current_email()
        values = ""

        try:
            values = self.get_body_argument("dbChanges")
            values = json.loads(values)  # z-values in dictionary
            print(values)
        except:
            pass
        if values:
            update_z_scores(id, email, values)
            self.redirect("/view-article?id=" + str(id))

        topic = ""
        direction = ""
        try:
            topic = self.get_body_argument("topicChange")
            direction = self.get_body_argument("directionChange")
        except:
            pass
        if topic and direction:
            update_vote(id, email, topic, direction)
            self.redirect("/view-article?id=" + str(id))


# API endpoint to handle search queries; returns 10 results at a time
class SearchEndpointHandler(BaseHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        database_dict = {}
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        option = self.get_query_argument("req", "t")
        results = formatted_search(q, start, option)
        response = {}
        output_list = []
        for article in results:
            try:
                article_dict = {}
                article_dict["id"] = article.pmid
                article_dict["title"] = article.title
                article_dict["authors"] = article.authors
                output_list.append(article_dict)
            except:
                pass
        response["articles"] = output_list
        if len(results) == 0:
            response["start_index"] = -1
            # returns -1 if there are no results;
            # UI can always calculate (start, end) with (start_index + 1, start_index + 1 + len(articles))
            # TODO: consider returning the start/end indices for the range of articles returned instead
        else:
            response["start_index"] = start
        self.write(json.dumps(response))


# API endpoint to fetch coordinates from all articles that match a query; returns 200 sets of coordinates at a time
class CoordinatesEndpointHandler(BaseHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        database_dict = {}
        q = self.get_query_argument("q", "")
        start = self.get_query_argument("start", 0)
        option = self.get_query_argument("req", "t")
        results = formatted_search(q, start, option, True)
        response = {}
        output_list = []
        for article in results:
            try:
                article_dict = {}
                experiments = json.loads(article.experiments)
                for c in experiments:  # get the coordinates from the experiments
                    output_list.extend(c["locations"])
            except:
                pass
        response["coordinates"] = output_list
        self.write(json.dumps(response))


# API endpoint that returns five random articles; used on the front page of Brainspell
class RandomEndpointHandler(BaseHandler):
    def get(self):
        self.set_header("Content-Type", "application/json")
        database_dict = {}
        results = random_search()
        response = {}
        output_list = []
        for article in results:
            try:
                article_dict = {}
                article_dict["id"] = article.pmid
                article_dict["title"] = article.title
                article_dict["authors"] = article.authors
                output_list.append(article_dict)
            except:
                pass
        response["articles"] = output_list
        self.write(json.dumps(response))


# account page
class AccountHandler(BaseHandler):
    def get(self):
        if self.is_logged_in():
            email = self.get_current_email()
            user = self.get_current_user()
            self.render('static/html/account.html', title=self.get_current_email(), username=user, message="",
                        password=self.get_current_password())
        else:
            self.redirect("/register")

    def post(self):
        hasher = hashlib.sha1()
        hasher2 = hashlib.sha1()
        newUsername = self.get_argument("newUserName")
        currPassword = self.get_argument("currentPassword").encode('utf-8')
        newPass = self.get_argument("newPassword").encode('utf-8')
        confirmPass = self.get_argument("confirmedPassword")
        name = self.get_current_email()
        user = self.get_current_user()
        hasher.update(currPassword)
        currPassword = hasher.hexdigest()
        username = self.get_current_email()

        """Checks for valid user entries"""
        if newUsername == None and currPassword == None:
            self.render('static/html/account.html', title=name, username=username, message="NoInfo")
        if newPass != confirmPass:
            self.render('static/html/account.html', title=name, username=username, message="mismatch")
        if currPassword != user.password:
            self.render('static/html/account.html', title=name, username=username, message="badPass")

        if newUsername:
            update = User.update(username=newUsername).where(User.emailaddress == name)
            update.execute()
        if newPass:
            hasher.update(newPass)
            newPass = hasher2.hexdigest()
            update = User.update(password=newPass).where(User.emailaddress == name)
            update.execute()
        self.redirect("/")


# contribute page
class ContributionHandler(BaseHandler):
    def get(self):
        name = self.get_current_email()
        self.render('static/html/contribute.html', title=name)


# API endpoint to get the contents of an article (called by the view-article page)
class ArticleEndpointHandler(BaseHandler):
    def get(self):
        id = self.get_query_argument("pmid")
        article = next(get_article(id))
        response = {}
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
        self.write(json.dumps(response))


# takes a file in JSON format and adds the articles to our database (called from the contribute page)
class BulkAddHandler(BaseHandler):
    def post(self):
        file_body = self.request.files['articlesFile'][0]['body'].decode('utf-8')
        contents = json.loads(file_body)
        if type(contents) == list:
            clean_articles = clean_bulk_add(contents)
            add_bulk(clean_articles)
            self.redirect("/?success=1")
        else:
            # data is malformed
            self.redirect("/?failure=1")


# API endpoint corresponding to BulkAddHandler
class BulkAddEndpointHandler(BaseHandler):
    def post(self):
        response = {}
        file_body = self.request.files['articlesFile'][0]['body'].decode('utf-8')
        contents = json.loads(file_body)
        if type(contents) == list:
            clean_articles = clean_bulk_add(contents)
            add_bulk(clean_articles)
            response["success"] = 1
        else:
            # data is malformed
            response["success"] = 0
        self.write(json.dumps(response))


# save an article to a user's account
class SaveArticleHandler(BaseHandler):  # TODO: change to a JSON endpoint
    def get(self):
        value = self.get_query_argument("id")
        if self.is_logged_in():
            User_metadata.insert(user_id=self.get_current_email(), article_pmid=value).execute()
            self.redirect("/account")
        else:
            self.redirect("/view-article?id=" + str(value))


# delete a saved article
class DeleteArticleHandler(BaseHandler):
    def get(self):
        if self.is_logged_in():
            value = self.get_query_argument("article")
            User_metadata.delete().where(User_metadata.user_id == self.get_current_email(),
                                         User_metadata.metadata_id == value).execute()
            self.write(json.dumps({"success": 1}))
        else:
            self.write(json.dumps({"success": 0}))


# access a user's saved articles
class SavedArticlesEndpointHandler(BaseHandler):
    def post(self):
        email = self.get_argument("email").encode("utf-8")
        password = self.get_argument("password").encode("utf-8")
        if user_login(email, password):
            articles = get_saved_articles(email)
            response = {}
            output_list = []
            for a in articles:
                pmid = a.article_pmid
                info = next(get_article(pmid))
                articleDict = {}
                articleDict["id"] = a.metadata_id
                articleDict["pmid"] = pmid
                articleDict["title"] = info.title
                articleDict["collection"] = a.collection
                output_list.append(articleDict)
            response["articles"] = output_list
            self.write(json.dumps(response))
        else:
            self.write(json.dumps({"success": 0}))


# save an article to a user's account
class SaveCollectionHandler(BaseHandler):
    def post(self):
        if self.is_logged_in():
            articles_encoded = self.request.arguments["articles[]"]  # TODO: look into "get_arguments" function
            collection_name = self.request.arguments["collection"][0].decode("utf-8")
            articles_decoded = []
            for a in articles_encoded:
                article = a.decode('utf-8')  # TODO: move save article operations to models.py
                User_metadata.insert(user_id=self.get_current_email(),
                                     article_pmid=article, collection=collection_name).execute()
        else:
            pass
            # self.redirect("/view-article?id=" + str(value))


class GithubLoginHandler(tornado.web.RequestHandler, torngithub.GithubMixin):
    @tornado.gen.coroutine
    def get(self):
        # we can append next to the redirect uri, so the user gets the
        # correct URL on login
        redirect_uri = url_concat(self.request.protocol
                                  + "://" + self.request.host
                                  + "/oauth",
                                  {"next": self.get_argument('next', '/')})

        # if we have a code, we have been authorized so we can log in
        if self.get_argument("code", False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                client_id=settings["github_client_id"],
                client_secret=settings["github_client_secret"],
                code=self.get_argument("code"))
            if user:
                self.set_secure_cookie("user", json_encode(user))
            else:
                self.clear_cookie("user")
            self.redirect(self.get_argument("next", "/"))
            return

        # otherwise we need to request an authorization code
        yield self.authorize_redirect(
            redirect_uri=redirect_uri,
            client_id=self.settings["github_client_id"],
            extra_params={"scope": "repo"})


class GithubLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        print("what is this next", self.get_argument("next", "/"))
        self.redirect(self.get_argument("next", "/"))


def parse_link(link):
    linkmap = {}
    for s in link.split(","):
        s = s.strip();
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

        gh_user = self.get_current_github_user()
        if gh_user["access_token"]:
            data = yield get_my_repos(self.get_auth_http_client(),
                                  gh_user['access_token'])
            repos = [d for d in data if d["name"].startswith("brainspell-collection")]
            print("repos are", [r["name"] for r in repos])
            if pmid:
                # TODO: Ideally this information would be store in the database
                # this is pretty hacky. I'm checking each collection for this pmid
                for repo in repos:
                    try:
                        sha_data = yield [torngithub.github_request(
                                          self.get_auth_http_client(),
                                          '/repos/{owner}/{repo}/contents/{path}'.format(owner=gh_user["login"],
                                          repo=repo["name"],
                                          path="{}.json".format(pmid)),
                        access_token=gh_user['access_token'],
                        method="GET")]

                        sha = [s["body"]["sha"] for s in sha_data]
                        if sha:
                            repo["in_collection"] = True
                    except tornado.auth.AuthError:
                        repo["in_collection"] = False

            if return_list:
                self.write(json_encode(repos))
            else:
                self.render("static/html/github-account.html",
                                info=repos,
                                github_user=gh_user["name"],
                                github_avatar=gh_user["avatar_url"])

        else:
            self.redirect("/oauth?next=/repos")



class NewRepoHandler(BaseHandler, torngithub.GithubMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        starttime = time.time()
        name = self.get_argument("name")
        desc = self.get_argument("description")
        if not name:
            self.write("")
        else:
            gh_user = self.get_current_github_user()
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
                access_token=gh_user['access_token'],
                method="POST",
                body=body)]
            data = []
            for res in ress:
                data.extend(res.body)

            endtime = time.time()
            # print(data)
            return self.redirect("/repos")


class NewFileHandler(BaseHandler, torngithub.GithubMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        starttime = time.time()
        collection = self.get_argument("collection")
        pmid = self.get_argument("pmid")
        entry = {"pmid": pmid,
                 "notes": "Here are my notes on this article"}
        content = b64encode(json_encode(entry).encode("utf-8")).decode('utf-8')
        gh_user = self.get_current_github_user()

        body = {
            "message": "adding {} to collection".format(pmid),
            "content": content
        }
        ress = yield [torngithub.github_request(
            self.get_auth_http_client(),
            '/repos/{owner}/{repo}/contents/{path}'.format(owner=gh_user["login"],
                                                           repo=collection,
                                                           path="{}.json".format(pmid)),
            access_token=gh_user['access_token'],
            method="PUT",
            body=body)]
        data = []
        for res in ress:
            data.extend(res.body)

        endtime = time.time()


class DeleteFileHandler(BaseHandler, torngithub.GithubMixin):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        starttime = time.time()
        collection = self.get_argument("collection")
        pmid = self.get_argument("pmid")
        entry = {"pmid": pmid,
                 "notes": "Here are my notes on this article"}
        content = b64encode(json_encode(entry).encode("utf=8"))
        gh_user = self.get_current_github_user()

        body = {
            "message": "deleting {} to collection".format(pmid),
        }

        sha_data = yield [torngithub.github_request(
            self.get_auth_http_client(),
            '/repos/{owner}/{repo}/contents/{path}'.format(owner=gh_user["login"],
                                                           repo=collection,
                                                           path="{}.json".format(pmid)),
            access_token=gh_user['access_token'],
            method="GET")]

        sha = [s["body"]["sha"] for s in sha_data][0]

        ress = yield [torngithub.github_request(
            self.get_auth_http_client(),
            '/repos/{owner}/{repo}/contents/{path}'.format(owner=gh_user["login"],
                                                           repo=collection,
                                                           path="{}.json".format(pmid)),
            access_token=gh_user['access_token'],
            method="DELETE",
            body={"sha": sha, "message": "removing {} from collection".format(pmid)})]


public_key = "private-key"
if "COOKIE_SECRET" in os.environ:
    public_key = os.environ["COOKIE_SECRET"]
assert public_key is not None, "The environment variable \"COOKIE_SECRET\" needs to be set."

if not "github_client_id" in os.environ:
    print("set your github_client_id env variable, and register your app at https://github.com/settings/developers")
    os.environ["github_client_id"] = "gh_client_id"
if not "github_client_secret" in os.environ:
    print("set your github_client_secret env variable, and register your app at https://github.com/settings/developers")
    os.environ["github_client_secret"] = "github_client_secret"

settings = {
    "cookie_secret": public_key,
    "login_url": "/login",
    "compress_response": True,
    "github_client_id": os.environ["github_client_id"],
    "github_client_secret": os.environ["github_client_secret"]
}


def make_app():
    return tornado.web.Application([
        (r"/static/(.*)", tornado.web.StaticFileHandler,
         {"path": os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'static')}),
        (r"/", MainHandler),
        (r"/json/query", SearchEndpointHandler),
        (r"/json/coordinates", CoordinatesEndpointHandler),  # TODO: add to API documentation on wiki
        (r"/json/random-query", RandomEndpointHandler),
        (r"/json/add-article", AddArticleEndpointHandler),
        (r"/json/article", ArticleEndpointHandler),
        (r"/json/delete-row", DeleteRowEndpointHandler),
        (r"/json/split-table", SplitTableEndpointHandler),
        (r"/json/flag-table", FlagTableEndpointHandler),
        (r"/json/bulk-add", BulkAddEndpointHandler),
        (r"/json/saved-articles", SavedArticlesEndpointHandler),
        (r"/json/delete-article", DeleteArticleHandler),
        (r"/login", LoginHandler),
        (r"/register", RegisterHandler),
        (r"/logout", LogoutHandler),
        (r"/account", AccountHandler),
        (r"/search", SearchHandler),
        (r"/view-article", ArticleHandler),
        (r"/contribute", ContributionHandler),
        (r"/bulk-add", BulkAddHandler),
        (r"/save-article", SaveArticleHandler),
        (r"/add-table-text", AddTableTextHandler),
        (r"/oauth", GithubLoginHandler),
        (r"/github_logout", GithubLogoutHandler),
        (r"/save-collection", SaveCollectionHandler),
        (r"/repos", ReposHandler),
        (r"/create_repo", NewRepoHandler),
        (r"/add-to-collection", NewFileHandler),
        (r"/remove-from-collection", DeleteFileHandler)
    ], debug=True, **settings)


if __name__ == "__main__":
    tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient",
                                                 defaults={"allow_nonstandard_methods": True})
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port)  # runs at localhost:5000
    print("Running Brainspell at http://localhost:5000...")
    tornado.ioloop.IOLoop.current().start()
