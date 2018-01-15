# all functions related to user accounts

import hashlib

from torngithub import json_decode

from models import *
# TODO: Updates to this file rely on removing json_encoding from the features using postgres Collection fields

def get_github_username_from_api_key(api_key):
    """ Fetch the GitHub username corresponding to a given API key. """

    user = User.select().where((User.password == api_key))
    user_obj = next(user.execute())
    return user_obj.username


def valid_api_key(api_key):
    """ Return whether an API key exists in our database. """

    user = User.select().where((User.password == api_key))
    return user.execute().count >= 1


def get_user_object_from_api_key(api_key):
    """ Return a PeeWee user object from an API key. """

    return User.select().where(User.password == api_key).execute()


def register_github_user(user_dict):
    """ Add a GitHub user to our database. """

    user_dict = json_decode(user_dict)

    # if the user doesn't already exist
    if (User.select().where(User.username ==
                            user_dict["login"]).execute().count == 0):
        username = user_dict["login"]
        email = user_dict["email"]
        hasher = hashlib.sha1()
        # password (a.k.a. API key) is a hash of the Github ID
        hasher.update(str(user_dict["id"]).encode('utf-8'))
        password = hasher.hexdigest()
        User.create(username=username, emailaddress=email, password=password)
        return True
    else:
        return False  # user already exists


def add_collection_to_brainspell_database(
        collection_name,
        description,
        api_key,
        cold_run=True):
    """ Create a collection in our database if it doesn't exist,
    or return false if the collection already exists. """

    if valid_api_key(api_key):
        user = list(get_user_object_from_api_key(api_key))[0]

        # get the dict of user collections
        if not user.collections:
            user_collections = {}
        else:
            # unfortunately, because malformatted JSON exists in our database,
            # we have to use eval instead of using JSON.decode()
            user_collections = eval(user.collections)

        # if the collection doesn't already exist
        if collection_name not in user_collections:
            # create the collection
            user_collections[collection_name] = {}
            user_collections[collection_name]["description"] = str(description)
            user_collections[collection_name]["pmids"] = []
            if not cold_run:
                q = User.update(
                    collections=user_collections).where(
                    User.username == user.username)
                q.execute()
            return True
    return False


def bulk_add_articles_to_brainspell_database_collection(
        collection, pmids, api_key, cold_run=True):
    """ Adds the PMIDs to collection_name, if such a collection exists under
    the given user. Assumes that the collection exists. Does not add repeats.

    Takes collection_name *without* "brainspell-collection".

    Return False if an assumption is violated, True otherwise. """

    user = get_user_object_from_api_key(api_key)
    if user.count > 0:
        user = list(user)[0]
        if user.collections:
            # assumes collections are well-formed JSON
            target = json_decode(user.collections)
            if collection not in target:
                target[collection] = {
                    "description": "None",
                    "pmids": []
                }

            pmid_set = set(map(lambda x: str(x), target[collection]["pmids"]))
            for pmid in pmids:
                pmid_set.add(str(pmid))

            target[collection]["pmids"] = list(pmid_set)
            if not cold_run:
                q = User.update(
                    collections=target).where(
                    User.password == api_key)
                q.execute()
            return True
        else:
            return False  # user has no collections; violates assumptions
    return False  # user does not exist


def remove_all_brainspell_database_collections(api_key):
    """ Dangerous! Drops all of a user's Brainspell collections
    from our local database. Does not affect GitHub.

    Called from CollectionsEndpointHandler."""

    if valid_api_key(api_key):
        q = User.update(
            collections={}).where(
            User.password == api_key)
        q.execute()


def get_brainspell_collections_from_api_key(api_key):
    """
    Return a user's collections from Brainspell's database given an API key.

    May be inconsistent with GitHub.
    """

    response = {}
    if valid_api_key(api_key):
        user = list(get_user_object_from_api_key(api_key))[0]
        if user.collections:
            return json_decode(user.collections)
    return response


def add_article_to_brainspell_database_collection(
        collection, pmid, api_key, cold_run=True):
    """
    Add a collection to our local database. Do not add to GitHub in this function.

    Assumes that the collection already exists. Assumes that the user exists.

    Takes collection_name *without* "brainspell-collection".
    Returns False if the article is already in the collection, or if an assumption
    is violated.

    This is an O(N) operation with respect to the collection size.
    If you're adding many articles, it's O(N^2). If you're adding multiple articles,
    please use bulk_add_articles_to_brainspell_database_collection.

    Called by AddToCollectionEndpointHandler.
    """

    user = get_user_object_from_api_key(api_key)
    if user.count > 0:
        user = list(user)[0]
        if user.collections:
            # assumes collections are well-formed JSON
            target = json_decode(user.collections)
            if collection not in target:
                target[collection] = {
                    "description": "None",
                    "pmids": []
                }
            pmids_list = set(
                map(lambda x: str(x), target[collection]["pmids"]))
            # provide a check for if the PMID is already in the collection
            if str(pmid) not in pmids_list:
                pmids_list.add(str(pmid))
                target[collection]["pmids"] = list(pmids_list)
                if not cold_run:
                    q = User.update(
                        collections=target).where(
                        User.password == api_key)
                    q.execute()
                return True
            else:
                return False  # article already in collection
        else:
            return False  # user has no collections; violates assumptions
    return False  # user does not exist


def remove_article_from_brainspell_database_collection(
        collection, pmid, api_key, cold_run=True):
    """ Remove an article from the Brainspell repo. Do not affect GitHub.

    Takes collection_name *without* "brainspell-collection".

    Similar implementation to add_article_to_brainspell_database_collection. """

    user = get_user_object_from_api_key(api_key)
    if user.count > 0:
        user = list(user)[0]
        if user.collections:
            # assumes collections are well-formed JSON
            target = json_decode(user.collections)
            if collection in target:
                pmids_list = list(
                    map(lambda x: str(x), target[collection]["pmids"]))
                if str(pmid) in pmids_list:
                    pmids_list.remove(str(pmid))
                    target[collection]["pmids"] = pmids_list
                    if not cold_run:
                        q = User.update(
                            collections=target).where(
                            User.password == api_key)
                        q.execute()
                    return True
                else:
                    return False  # article not in collection
            else:
                return False  # collection doesn't exist
        else:
            return False  # user has no collections; violates assumptions
    return False  # user does not exist
