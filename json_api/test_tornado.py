""" To run this file, run `py.test -v test_tornado.py`. """

import tornado.web
import os
import pytest
import brainspell
from search import *
import autopep8
import json_api
import user_interface_handlers
#import selenium
#from selenium import webdriver
#from selenium.webdriver.support.ui import WebDriverWait


application = brainspell.make_app()


"""Configuring SauceLabs for Selenium Testing"""

"""
capabilities = {}
username = os.environ["SAUCE_USERNAME"]
access_key = os.environ["SAUCE_ACCESS_KEY"]
capabilities["tunnel-identifier"] = os.environ["TRAVIS_JOB_NUMBER"]
hub_url = "%s:%s@localhost:4445" % (username, access_key)
capabilities["build"] = os.environ["TRAVIS_BUILD_NUMBER"]
capabilities["tags"] = [os.environ["TRAVIS_PYTHON_VERSION"], "CI"]
capabilities["browserName"] = "firefox"
driver = webdriver.Remote(
    desired_capabilities=capabilities,
    command_executor="http://%s/wd/hub" %
    hub_url)
"""

"""
TODO: need to make tests for:
1) user creation
2) user login
3) adding and deleting a row of coordinates
4) splitting, flagging a table
5) voting on table and article tags
6) setting the authors for an article
7) saving to a GitHub collection
"""

# Enforces a data access object abstraction layer


def test_no_reference_to_models_in_endpoints():
    files_to_enforce = ["json_api.py", "user_interface_handlers.py"]
    for f in files_to_enforce:
        with open(f, "r") as python_file_handler:
            python_contents = python_file_handler.read()
            assert ("from models import" not in python_contents) and ("import models" not in python_contents), "You should not access the models directly in your handler. The file " + \
                f + " should be rewritten to no longer import models, and instead use a layer of abstraction (so that we can reimplement our data access layer if needed)."

# Tests that there are no EndpointHandlers in the user_interface_handlers file.


def test_endpoint_handlers_are_in_the_correct_file():
    assert len([f for f in dir(user_interface_handlers) if "EndpointHandler" in f]
               ) == 0, "There is an EndpointHandler in the user_interface_handlers file. Please move this to json_api."

# Tests that EndpointHandlers (JSON API endpoints) conform to the
# specification by implementing either pull_api, push_api, post_pull_api,
# or post_push_api


def test_endpoint_handlers_implementation():
    for endpoint in [f for f in dir(json_api) if "EndpointHandler" in f]:
        func = eval("json_api." + endpoint)
        assert func.pull_api or func.push_api or func.post_pull_api or func.post_push_api, "The class " + endpoint + \
            " does not implement either pull_api, push_api, post_pull_api, or post_push_api. Please reimplement the class to conform to this specification."

# Tests whether requirements.txt is alphabetized (important to identify
# missing/redundant requirements)


def test_requirements_file_is_sorted():
    with open('../requirements.txt') as f:
        lines = f.readlines()
    assert sorted(lines) == lines, "The requirements.txt file is not sorted."

# Tests for PEP8 style


def test_python_style_check():
    files_in_directory = os.listdir()
    for f in files_in_directory:
        if os.path.splitext(f)[1] == ".py":
            with open(f, "r") as python_file_handler:
                python_contents = python_file_handler.read()
                assert autopep8.fix_code(python_contents, options={'aggressive': 2}) == python_contents, "Style check failed on " + f + \
                    ". Run `autopep8 --in-place --aggressive --aggressive " + f + "`, or `autopep8 --in-place --aggressive --aggressive *.py`"

# Asserts search results appearing for commonly found target


def test_search():
    assert len(formatted_search("brain", 0)) > 0

# Asserts Procfile in proper place. (Required for Heroku build)


def test_procfile():
    with open("../Procfile", "r") as f:
        contents = f.read()
        filename = contents.replace(
            "web: python3 json_api/",
            "").replace(
            "\n",
            "")
        assert filename in os.listdir()


""" TODO: get selenium testing working
def test_existence(): #Using selenium testing
    driver.get("https://brainspell.herokuapp.com")
    assert "Brainspell" in driver.title #Checks website title is accurate

    #Ensuring elements of view article page are all present
    driver.get("https://brainspell.herokuapp.com/view-article?id=00000000")
    meshButtons = driver.find_elements_by_class_name("dropbtn")
    assert meshButtons != None #Ensure Mesh terms are included
    table = driver.find_elements_by_class_name("experiment-table-row")
    assert table != None

    #Click and vote on a MeSH tag
    try:
        myElem = WebDriverWait(driver,5)
        buttons = driver.find_elements_by_class_name("dropbtn")
        buttons[0].click()
        assert "modal-body" in driver.page_source
    except:
        pass
    driver.find_element_by_id("closer").click()

    #Test search page TODO: Only works when user logged in
    # driver.get("https://brainspell.herokuapp.com/search?q=brain&req=t")
    # items = driver.find_elements_by_class_name("must-login")
    # assert len(items) > 9

    #Make sure showing the widget doesn't break regardless of article
    #TODO: Find a way to wait until the page is ready
    # driver.find_element_by_id("widgetOption").click()
"""

# tests that the Tornado application is successfully built


@pytest.fixture
def app():
    return application

# tests that the base_url is returning a 200 code (good)


@pytest.mark.gen_test
def test_front_page(http_client, base_url):
    response = yield http_client.fetch(base_url)
    assert response.code == 200
