# all functions related to user accounts

from torngithub import json_decode
from models import *

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
