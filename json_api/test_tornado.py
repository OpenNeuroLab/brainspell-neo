import tornado.web
import os
import pytest
import brainspell
import models
import search

application = brainspell.make_app()

"""
TODO: need to make tests for:
1) user creation 
2) user login
3) adding and deleting a row of coordinates
4) splitting, flagging a table
5) voting on table and article tags
6) setting the authors for an article
7) saving to a brainspell.org collection, and to a GitHub collection
"""

def test_search():
    assert len(search.formatted_search("brain", 0)) > 0

def test_procfile():
    f = open("../Procfile", "r")
    contents = f.read()
    filename = contents.replace("web: python3 json_api/", "").replace("\n", "")
    assert filename in os.listdir()

@pytest.fixture
def app():
    return application

@pytest.mark.gen_test
def test_front_page(http_client, base_url):
    response = yield http_client.fetch(base_url)
    assert response.code == 200
