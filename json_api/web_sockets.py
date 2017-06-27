import json

import tornado.websocket

from article_helpers import *


# abstract class for general WebSocket handler
class BaseSocket(tornado.websocket.WebSocketHandler):
    receive = None

    def open(self):
        # setup
        pass

    def on_message(self, message):
        # receives a JSON formatted message
        response = {
            "success": 1
        }

        messageDict = json.loads(message)

        assert self.receive is not None, "You haven't implemented this WebSocket"
        response = self.receive(messageDict, response)

        self.write_message(response)

    def on_close(self):
        # cleanup
        pass


class ViewArticleWebSocket(BaseSocket):
    def receive(self, message, response):

        if message["type"] == "update-table-vote":
            payload = message["payload"]
            tag_name = payload["tag_name"]
            direction = payload["direction"]
            table_num = payload["table_num"]
            pmid = payload["id"]
            column = payload["column"]
            user = payload["username"]
            print(table_num)
            update_table_vote(
                tag_name,
                direction,
                table_num,
                pmid,
                column,
                user)
        elif message["type"] == "delete-row":
            pass  # TODO: implement
        else:
            # message type is invalid
            response["success"] = 0

        return response
