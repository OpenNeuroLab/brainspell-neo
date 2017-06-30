import json
from enum import Enum

import tornado
import tornado.web
from torngithub import json_decode

from user_accounts import *


class Endpoint(Enum):
    """ 
    An Enum to distinguish push from pull APIs.
    Push APIs need to validate the user's API key.
    """

    PUSH_API = 1
    PULL_API = 2


class BaseHandler(tornado.web.RequestHandler):
    """ A handler that all Brainspell handlers should extend. """
    endpoint_type = None

    def get_safe_arguments(self, arguments_dict, accessor):
        """ Enforce type safety; do not verify API key. """

        args = {}
        for k in self.parameters:
            if k not in arguments_dict:
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
        """
        Provide a guarantee for a valid API key on PUSH endpoints,
        documentation at /help, and type-checked arguments.
        """

        assert self.endpoint_type, "You must indicate what type of endpoint this is by setting the endpoint_type variable."
        self.set_header("Content-Type", "application/json")

        assert self.parameters is not None, "You haven't indicated the parameters for this endpoint."

        # provide help documentation
        components = [x for x in self.request.path.split("/") if x]
        if len(components) >= 3 and components[2] == "help":
            formatted_parameters = {}
            for p in self.parameters:
                formatted_parameters[p] = {}
                if "default" not in self.parameters[p]:
                    formatted_parameters[p]["required"] = True
                else:
                    formatted_parameters[p]["required"] = False
                    formatted_parameters[p]["default"] = self.parameters[p]["default"]
                type_name = self.parameters[p]["type"].__name__
                if type_name == "loads": # account for loads function
                    type_name = "json"
                formatted_parameters[p]["type"] = type_name
            if self.endpoint_type == Endpoint.PUSH_API:
                formatted_parameters["key"] = {}
                formatted_parameters["key"]["required"] = True
                formatted_parameters["key"]["type"] = str.__name__
            self.write(json.dumps({
                "success": 1,
                "parameters": formatted_parameters
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
        """ 
        Render a Tornado HTML template, automatically
        appending user information
        """

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
        """
        Return an object representing the user's name, avatar, and
        access_token, or None is the user is not logged in.
        Technically a "private" method; please use the get_current_* methods.
        """

        try:
            return json_decode(self.get_secure_cookie("user"))
        except BaseException:
            return None

    def get_current_github_name(self):
        """ Get the user's name from GitHub. """

        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["name"]
        return ""

    def get_current_github_username(self):
        """ 
        Get the user's GitHub username. Guaranteed to exist if logged in.
        """

        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["login"]
        return ""

    def get_current_github_avatar(self):
        """ Get the user's avatar from GitHub. """

        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["avatar_url"]
        return ""

    def get_current_github_access_token(self):
        """ 
        Get the user's access token from GitHub. Guaranteed to exist if logged in. 
        """

        github_user_object = self.__get_current_github_object__()
        if github_user_object:
            return github_user_object["access_token"]
        return ""

    def get_current_api_key(self):
        """
        Get the user's API key. Guaranteed to exist if logged in. 
        """

        return self.get_secure_cookie("api_key")

    def set_default_headers(self):
        """ 
        Set the headers to allow JS API requests. Potentially a security concern.
        """

        origin = self.request.headers.get('Origin')
        if origin:
            self.set_header('Access-Control-Allow-Origin', origin)
        self.set_header('Access-Control-Allow-Credentials', 'true')
