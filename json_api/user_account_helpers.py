import tornado
from models import *
import simplejson
from torngithub import json_decode

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

def user_login(email, password):
    user = User.select().where((User.emailaddress == email) & (User.password == password))
    return user.execute().count == 1