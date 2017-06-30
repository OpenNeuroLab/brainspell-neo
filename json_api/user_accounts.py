# all functions related to user accounts

from torngithub import json_decode
from torngithub import json_encode

from models import *


def get_user_object(user):
    """ Return a PeeWee object representing a single user. """

    q = User.select().where(User.emailaddress == user)
    return q.execute()


def get_github_username_from_api_key(api_key):
    """ Fetch the GitHub username corresponding to a given API key. """

    user = User.select().where((User.password == api_key))
    user_obj = next(user.execute())
    return user_obj.username


def valid_api_key(api_key):
    """ Return whether an API key exists in our database. """

    user = User.select().where((User.password == api_key))
    return user.execute().count >= 1


def register_github_user(user_dict):
    """ Add a GitHub user to our database. """

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
    """ Return whether a given repo already exists in our local database. """

    user = User.select().where(User.username == username).execute()
    if user.count > 0:
        user = list(user)[0]
    else:
        return False  # Failure TODO: Indicate Failure
    if not user.collections:
        target = {}
    else:
        target = json_decode(user.collections)
    if name in target:
        return False  # Trying to create a pre-existing repo, TODO: Indicate Failure
    target[name] = []
    q = User.update(
        collections=json_encode(target)).where(
        User.username == username)
    q.execute()
    return True


def add_to_repo(collection, pmid, username):
    """ Add a collection to our local database. Do not add to GitHub in this function. """

    collection = collection.replace("brainspell-collection-", "")
    user = User.select().where(User.username == username).execute()
    if user.count > 0:
        user = list(user)[0]
    else:
        return False
    if not user.collections:
        target = {}
    else:
        target = json_decode(user.collections)
    if collection not in target:
        target[collection] = []
    target[collection].append(pmid)
    q = User.update(
        collections=json_encode(target)).where(
        User.username == username)
    q.execute()
    return True


def remove_from_repo(collection, pmid, username):
    """ Remove an article from a repo/collection. """

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
