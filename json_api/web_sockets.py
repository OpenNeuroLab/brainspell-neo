import json

import tornado.websocket

import json_api
from article_helpers import *
from base_handler import *
from user_accounts import *

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def convert(name):
    s1 = first_cap_re.sub(r'\1-\2', name)
    return all_cap_re.sub(r'\1-\2', s1).lower()


endpoints = {}
for endpoint in [f for f in dir(json_api) if "EndpointHandler" in f]:
    func = eval("json_api." + endpoint)
    name = convert(endpoint.replace("EndpointHandler", ""))
    endpoints[name] = func

# WebSocket implementation of all JSON endpoints


class EndpointWebSocket(tornado.websocket.WebSocketHandler):
    def open(self):
        # setup
        pass

    def on_message(self, message):
        # receives a JSON formatted message
        response = {
            "success": 1
        }

        messageDict = json.loads(message)

        if messageDict["type"] not in endpoints:
            self.write_message({
                "success": 0,
                "description": "Endpoint undefined."
            })
        else:
            func = endpoints[messageDict["type"]]
            payload = {}
            if "payload" in messageDict:
                payload = messageDict["payload"]

            argsDict = BaseHandler.get_safe_arguments(
                func, payload, lambda k: payload[k])

            if argsDict["success"] == 1:
                # validate API key if push endpoint
                if func.endpoint_type == Endpoint.PULL_API or (
                    func.endpoint_type == Endpoint.PUSH_API and valid_api_key(
                        argsDict["args"]["key"])):
                    response = {"success": 1}
                    response = func.process(func, response, argsDict["args"])
                    self.write_message(json.dumps(response))
                else:
                    self.write_message(json.dumps(
                        {"success": 0, "description": "Invalid API key."}))
            else:
                # print the error message from argument parsing
                self.write_message(json.dumps(argsDict))

    def on_close(self):
        # cleanup
        pass
