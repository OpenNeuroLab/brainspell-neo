import json

import tornado.websocket

import json_api
from article_helpers import *
from base_handler import *
from user_account_helpers import *

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def convert(name):
    """ Convert from camelCase to hyphenated-names. """
    s1 = first_cap_re.sub(r'\1-\2', name)
    return all_cap_re.sub(r'\1-\2', s1).lower()


# map the hyphenated names to the corresponding classes (endpoints)
endpoints = {}
for endpoint in [f for f in dir(json_api) if "EndpointHandler" in f]:
    func = eval("json_api." + endpoint)
    name = convert(endpoint.replace("EndpointHandler", ""))
    if func.api_version != 1:
        name = "v" + str(func.api_version) + "/" + name
    endpoints[name] = func


class EndpointWebSocket(tornado.websocket.WebSocketHandler):
    """ Allow developers to access the JSON API via WebSockets.
    Only works for synchronous handlers. """

    def open(self):
        # setup
        pass

    def on_message(self, message):
        """
        Receive a JSON formatted message, parse the arguments,
        and pass the resulting arguments dictionary to the processing
        function of the corresponding JSON API class. Return the response.
        """

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

            self.write_message(json.dumps(api_call(func, payload)))

    def on_close(self):
        # cleanup
        pass

    # set_default_headers = BaseHandler.set_default_headers


def api_call(func, args={}):
    """ Return the output of a call to an endpoint, given an arguments dict.

    Take the name of an Endpoint class and an arguments dict, where the keys
    of the arguments dict are those specified in the Endpoint.parameters dict,
    plus the "key" parameter, if the endpoint is a PUSH_API endpoint.

    (For a complete list of arguments for an endpoint, go to
        http://localhost:5000/json/{ENDPOINT_NAME}/help)

    Do not modify the args dict passed in.

    Ex:
    >>> api_call(RandomQueryEndpointHandler)
    {
       'success': 1,
       'articles': [
          {
             'id': '22357844',
             'title': 'Linking pain and the body: neural correlates of visually induced analgesia.',
             'authors': 'Longo MR,Iannetti GD,Mancini F,Driver J,Haggard P'
          },
          ...
       ]
    }

    >>> api_call(QueryEndpointHandler, {
        "q": "brain"
        })
    {
       'success': 1,
       'articles': [
          {
             'id': '15858160',
             'title': 'Dissociable roles of prefrontal and anterior cingulate cortices in deception.',
             'authors': 'Abe N,Suzuki M,Tsukiura T,Mori E,Yamaguchi K,Itoh M,Fujii T'
          },
          ...
       ],
       'start_index': 0
    }
    """

    argsDict = BaseHandler.get_safe_arguments(
        func, args, lambda k: args[k])

    if argsDict["success"] == 1:
        # validate API key if push endpoint
        if func.endpoint_type == Endpoint.PULL_API or (
            func.endpoint_type == Endpoint.PUSH_API and valid_api_key(
                argsDict["args"]["key"])):
            response = {
                "success": 1
            }
            response = func.process(func, response, argsDict["args"])
            return response
        else:
            return {"success": 0, "description": "Invalid API key."}
    # print the error message from argument parsing, if get_safe_arguments
    # failed
    return argsDict
