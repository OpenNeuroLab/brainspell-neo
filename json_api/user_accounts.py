# all functions related to user accounts

import tornado
from models import *
import simplejson
from torngithub import json_decode

class BaseHandler(tornado.web.RequestHandler): 
    """
    TODO: need to establish standard way of: 
    1) verifying that a user is logged in before showing them a UI page (currently we don't do this)
    """
    push_api = None
    pull_api = None

    def get(self):
        assert not self.push_api or not self.pull_api, "You cannot set this endpoint as both a push API and pull API endpoint."
        self.set_header("Content-Type", "application/json")
        if self.push_api:
            api_key = self.get_query_argument("key", "")
            if valid_api_key(api_key):
                response = {"success": 1}
                response = self.push_api(response)
                self.write(json.dumps(response))
            else:
                self.write(json.dumps({"success": 0}))
        elif self.pull_api:
            response = {"success": 1}
            response = self.pull_api(response)
            self.write(json.dumps(response))
        else:
            print("GET endpoint undefined.")
    
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

def get_saved_articles(email):
    return User_metadata.select().where(User_metadata.user_id==email).execute()
    
def get_user(user): # TODO: have a naming convention for functions that return PeeWee objects
    q = User.select().where(User.emailaddress==user)
    return q.execute()

def get_email_from_api_key(api_key):
    user = User.select().where((User.password == api_key)) # using password hashes as API keys for now; can change later
    userInfo = next(user.execute())
    return userInfo.emailaddress

def valid_api_key(api_key):
    user = User.select().where((User.password == api_key)) # using password hashes as API keys for now; can change later
    return user.execute().count >= 1

def insert_user(user, pw, email): # TODO: what is the difference between this and "register_user"? this is just the more dangerous option?
    q = User.create(username = user, password = pw, emailaddress = email)
    q.execute()

def register_user(username,email,password):
    if (User.select().where((User.emailaddress == email)).execute().count == 0):
        hasher=hashlib.sha1()
        hasher.update(password)
        password = hasher.hexdigest()
        User.create(username = username, emailaddress = email, password = password)
        return True
    else:
        return False