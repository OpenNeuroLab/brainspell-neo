# all functions related to user accounts

import json

import simplejson
import tornado
import tornado.web
from torngithub import json_decode

from models import *


class BaseHandler(tornado.web.RequestHandler):
    push_api = None
    pull_api = None
    post_push_api = None
    post_pull_api = None

    def get_safe_arguments(self):
        # enforce type safety
        argumentSuccess = True
        args = {}
        for k in self.parameters:
            if k not in self.request.arguments:
                if "default" not in self.parameters[k]:
                    self.write(json.dumps({
                        "success": 0,
                        "description": "Missing required parameter: " + k
                    }))
                    argumentSuccess = False
                    return {
                        "success": argumentSuccess,
                        "args": args
                    }
                else:
                    args[k] = self.parameters[k]["type"](
                        self.parameters[k]["default"])
            else:
                try:
                    args[k] = self.parameters[k]["type"](self.get_argument(k))
                except BaseException:
                    self.write(
                        json.dumps(
                            {
                                "success": 0,
                                "description": "Bad input for argument (type " +
                                self.parameters[k]["type"].__name__ +
                                "): " +
                                k}))
                    argumentSuccess = False
                    return {
                        "success": argumentSuccess,
                        "args": args
                    }

        if self.push_api or self.post_push_api or (
                "key" in self.request.arguments):
            args["key"] = str(self.get_argument("key", ""))

        return {
            "success": argumentSuccess,
            "args": args
        }

    def get(self):
        assert not self.push_api or not self.pull_api, "You cannot set this endpoint as both a push API and pull API endpoint."
        self.set_header("Content-Type", "application/json")

        assert self.parameters is not None, "You haven't indicated the parameters for this endpoint."

        argsDict = self.get_safe_arguments()

        if argsDict["success"]:
            if self.push_api:
                api_key = self.get_query_argument("key", "")
                if valid_api_key(argsDict["args"]["key"]):
                    response = {"success": 1}
                    response = self.push_api(response, argsDict["args"])
                    self.write(json.dumps(response))
                else:
                    self.write(json.dumps({"success": 0}))
            elif self.pull_api:
                response = {"success": 1}
                response = self.pull_api(response, argsDict["args"])
                self.write(json.dumps(response))
            else:
                print("GET endpoint undefined.")

    # TODO: at some point, we might want to consider making all GET and POST
    # endpoints identical
    def post(self):
        assert not self.post_push_api or self.post_pull_api, "You cannot set this POST endpoint as both a push API and pull API endpoint."
        self.set_header("Content-Type", "application/json")

        assert self.parameters is not None, "You haven't indicated the parameters for this endpoint."

        argsDict = self.get_safe_arguments()

        if argsDict["success"]:
            if self.post_push_api:
                if valid_api_key(argsDict["args"]["key"]):
                    response = {"success": 1}
                    response = self.post_push_api(response, argsDict["args"])
                    self.write(json.dumps(response))
                else:
                    self.write(json.dumps({"success": 0}))
            elif self.post_pull_api:
                response = {"success": 1}
                response = self.post_pull_api(response, argsDict["args"])
                self.write(json.dumps(response))
            else:
                print("POST endpoint undefined.")

    def render_with_user_info(self, url, params):
        # a helper function that renders a Tornado HTML template, automatically
        # appending user information
        login_dict = {
            "github_name": self.get_current_github_name(),
            "github_username": self.get_current_github_username(),
            "github_avatar": self.get_current_github_avatar(),
            "api_key": self.get_current_api_key()
        }
        for k in params:
            # rather than passing both dicts, make it 3.4 compatible by merging
            login_dict[k] = params[k]
        self.render(url, **login_dict)

    def __get_current_github_object__(self):
        # returns an object representing the user's name, avatar, and
        # access_token, or None is the user is not logged in
        try:
            return json_decode(self.get_secure_cookie("user"))
        except BaseException:
            return None

    def get_current_github_name(self):
        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["name"]
        return ""

    def get_current_github_username(self):
        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["login"]
        return ""

    def get_current_github_avatar(self):
        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["avatar_url"]
        return ""

    def get_current_github_access_token(self):
        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["access_token"]
        return ""

    def get_current_api_key(self):
        return self.get_secure_cookie("api_key")

    # allow CORS
    def set_default_headers(self):
        origin = self.request.headers.get('Origin')
        if origin:
            self.set_header('Access-Control-Allow-Origin', origin)
        self.set_header('Access-Control-Allow-Credentials', 'true')


# TODO: have a naming convention for functions that return PeeWee objects
# (*_object?)
def get_user_object(user):
    q = User.select().where(User.emailaddress == user)
    return q.execute()


def get_github_username_from_api_key(api_key):
    user = User.select().where((User.password == api_key))
    user_obj = next(user.execute())
    return user_obj.username


def valid_api_key(api_key):
    user = User.select().where((User.password == api_key))
    return user.execute().count >= 1


def register_github_user(user_dict):
    user_dict = json_decode(user_dict)
    if (User.select().where(User.username ==
                            user_dict["login"]).execute().count == 0):
        username = user_dict["login"]
        password = str(user_dict["id"])  # Password is a hash of the Github ID
        email = user_dict["email"]
        hasher = hashlib.sha1()
        hasher.update(password.encode('utf-8'))
        password = hasher.hexdigest()
        User.create(username=username, emailaddress=email, password=password)
        return True
    else:
        return False  # User already exists


def new_repo(name, username):
    user = User.select().where(User.username == username).execute()
    if user.count > 0:
        user = list(user)[0]
    else:
        return False  # Failure TODO: Indicate Failure
    target = eval(user.collections)
    if not target:
        target = {}
    if name in target:
        return False  # Trying to create a pre-existing repo, TODO: Indicate Failure
    target[name] = []
    q = User.update(collections=target).where(User.username == username)
    q.execute()
    return True


def add_to_repo(collection, pmid, username):
    collection = collection.replace("brainspell-collection-", "")
    user = User.select().where(User.username == username).execute()
    if user.count > 0:
        user = list(user)[0]
    else:
        return False
    target = eval(user.collections)
    target[collection].append(pmid)
    q = User.update(collections=target).where(User.username == username)
    q.execute()
    return True


def remove_from_repo(collection, pmid, username):
    collection = collection.replace("brainspell-collection-", "")
    user = User.select().where(User.username == username).execute()
    if user.count > 0:
        user = list(user)[0]
    else:
        return False  # Incorrect Username passed
    target = eval(user.collections)
    if pmid in target[collection]:
        target[collection].remove(pmid)
    else:
        return False  # Trying to remove an article that's not there
    q = User.update(collections=target).where(User.username == username)
    q.execute()
    return True
