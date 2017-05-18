import tornado.web
import os
import pytest
import brainspell
import models
import search
import selenium
from selenium import webdriver

application = brainspell.make_app()


"""Configuring SauceLabs for Selenium Testing"""
capabilities = {}
username = os.environ["SAUCE_USERNAME"]
access_key = os.environ["SAUCE_ACCESS_KEY"]
capabilities["tunnel-identifier"] = os.environ["TRAVIS_JOB_NUMBER"]
hub_url = "%s:%s@localhost:4445" % (username, access_key)
capabilities["build"] = os.environ["TRAVIS_BUILD_NUMBER"]
capabilities["tags"] = [os.environ["TRAVIS_PYTHON_VERSION"], "CI"]
driver = webdriver.Remote(desired_capabilities=capabilities, command_executor="http://%s/wd/hub" % hub_url)

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
# Asserts search results appearing for commonly found target
def test_search():
    assert len(search.formatted_search("brain", 0)) > 0

#Asserts Procfile in proper place. (Required for Heroku build)
def test_procfile():
    f = open("../Procfile", "r")
    contents = f.read()
    filename = contents.replace("web: python3 json_api/", "").replace("\n", "")
    assert filename in os.listdir()

def test_row_add(): #Using selenium testing
    driver.get("https://brainspell.herokuapp.com")
    assert "Brainspell" in driver.title #Checks website title is accurate
    driver.get("https://brainspell.herokuapp.com/view-article?id=00000000")
    assert driver.find_element_by_id("110690") != None #Entry fields for Z-
    meshButtons = driver.find_elements_by_class_name("dropbtn")
    assert meshButtons != None #Ensure Mesh terms are included





# TODO: What does this test do?
@pytest.fixture
def app():
    return application

# TODO: What does this test do?
@pytest.mark.gen_test
def test_front_page(http_client, base_url):
    response = yield http_client.fetch(base_url)
    assert response.code == 200

