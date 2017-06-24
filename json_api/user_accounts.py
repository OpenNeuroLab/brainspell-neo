# all functions related to user accounts

import tornado
from models import *
import simplejson
from torngithub import json_decode
import tornado.web
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
            for user in get_user(self.get_current_github_user()):
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


    def set_default_headers(self):
        origin = self.request.headers.get('Origin')
        if origin:
            self.set_header('Access-Control-Allow-Origin', origin)
        self.set_header('Access-Control-Allow-Credentials', 'true')

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

def register_github_user(user_dict):
    user_dict = json_decode(user_dict)
    if (User.select().where(User.username == user_dict["login"]).execute().count == 0):
        username = user_dict["login"]
        password = str(user_dict["id"]) #Password is a hash of the Github ID
        email = user_dict["email"]
        hasher = hashlib.sha1()
        hasher.update(password.encode('utf-8'))
        password = hasher.hexdigest()
        User.create(username=username,emailaddress=email,password=password)
        return True
    else:
        return False #User already exists

def new_repo(name,username):
    user = User.select().where(User.username == username).execute()
    if user.count > 0:
        user = list(user)[0]
    else:
        return False #Failure TODO: Indicate Failure
    target = eval(user.collections)
    if not target:
        target = {}
    if name in target:
        return False #Trying to create a pre-existing repo, TODO: Indicate Failure
    target[name] = []
    q = User.update(collections = target).where(User.username == username)
    q.execute()
    return True

def add_to_repo(collection, pmid, username):
    collection = collection.replace("brainspell-collection-","")
    user = User.select().where(User.username == username).execute()
    if user.count > 0:
        user = list(user)[0]
    else:
        return False
    target = eval(user.collections)
    target[collection].append(pmid)
    q = User.update(collections = target).where(User.username == username)
    q.execute()
    return True


def remove_from_repo(collection, pmid, username):
    collection = collection.replace("brainspell-collection-","")
    user = User.select().where(User.username == username).execute()
    if user.count > 0:
        user = list(user)[0]
    else:
        return False #Incorrect Username passed
    target = eval(user.collections)
    if pmid in target[collection]:
        target[collection].remove(pmid)
    else:
        return False #Trying to remove an article that's not there
    q = User.update(collections = target).where(User.username == username)
    q.execute()
    return True
