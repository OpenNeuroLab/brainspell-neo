import json
from enum import Enum

import tornado
import tornado.web
from torngithub import json_decode

from user_accounts import *


class Endpoint(Enum):
    PUSH_API = 1
    PULL_API = 2


class BaseHandler(tornado.web.RequestHandler):
    endpoint_type = None

    def get_safe_arguments(self, argumentsDict, accessor):
        # enforce type safety; does not verify API key
        args = {}
        for k in self.parameters:
            if k not in argumentsDict:
                if "default" not in self.parameters[k]:
                    return {
                        "success": 0,
                        "description": "Missing required parameter: " + k
                    }
                else:
                    args[k] = self.parameters[k]["type"](
                        self.parameters[k]["default"])
            else:
                try:
                    args[k] = self.parameters[k]["type"](accessor(k))
                except BaseException:
                    return {
                        "success": 0,
                        "description": "Bad input for argument (type " +
                        self.parameters[k]["type"].__name__ +
                        "): " +
                        k}

        if self.endpoint_type == Endpoint.PUSH_API or (
                "key" in self.request.arguments):
            try:
                args["key"] = str(accessor("key"))
            except BaseException:
                args["key"] = ""

        return {
            "success": 1,
            "args": args
        }

    def get(self):
        # provides guarantee for API key on PUSH endpoints, and documentation
        # at /help
        assert self.endpoint_type, "You must indicate what type of endpoint this is by setting the endpoint_type variable."
        self.set_header("Content-Type", "application/json")

        assert self.parameters is not None, "You haven't indicated the parameters for this endpoint."

        # provide help documentation
        components = [x for x in self.request.path.split("/") if x]
        if len(components) >= 3 and components[2] == "help":
            formattedParameters = {}
            for p in self.parameters:
                formattedParameters[p] = {}
                if "default" not in self.parameters[p]:
                    formattedParameters[p]["required"] = True
                else:
                    formattedParameters[p]["required"] = False
                    formattedParameters[p]["default"] = self.parameters[p]["default"]
                formattedParameters[p]["type"] = self.parameters[p]["type"].__name__
            if self.endpoint_type == Endpoint.PUSH_API:
                formattedParameters["key"] = {}
                formattedParameters["key"]["required"] = True
                formattedParameters["key"]["type"] = str.__name__
            self.write(json.dumps({
                "success": 1,
                "parameters": formattedParameters
            }))
        else:
            # type check arguments
            argsDict = self.get_safe_arguments(
                self.request.arguments, self.get_argument)

            if argsDict["success"] == 1:
                # validate API key if push endpoint
                if self.endpoint_type == Endpoint.PULL_API or (
                    self.endpoint_type == Endpoint.PUSH_API and valid_api_key(
                        argsDict["args"]["key"])):
                    response = {"success": 1}
                    response = self.process(response, argsDict["args"])
                    self.write(json.dumps(response))
                else:
                    self.write(json.dumps({"success": 0}))
            else:
                # print the error message from argument parsing
                self.write(json.dumps(argsDict))

    post = get

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
