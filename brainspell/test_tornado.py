""" To run this file, run `py.test -v test_tornado.py`. """

import hashlib
import os

import autopep8
import pytest
import tornado.web

import brainspell
import github_collections
import json_api
import user_interface
from search_helpers import *

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
7) saving to and deleting from a GitHub collection
"""


def test_abstraction_layer():
    """
    Enforce a data access object abstraction layer.
    Enforce using self.render_with_user_info, instead of self.render.
    Enforce only rendering HTML templates in the user_interface
    module.
    """

    files_to_enforce = [
        "json_api.py",
        "user_interface.py",
        "github_collections.py"]
    for f in files_to_enforce:
        with open(f, "r") as python_file_handler:
            python_contents = python_file_handler.read()
            assert ("from models import" not in python_contents) and ("import models" not in python_contents), "You should not access the models directly in your handler. The file " + \
                f + " should be rewritten to no longer import models, and instead use a layer of abstraction (so that we can reimplement our data access layer if needed)."
            if f == "json_api.py" or f == "github_collections.py":
                assert "self.render" not in python_contents, "The file " + f + \
                    " appears to render an HTML template. Please move this to the 'user_interface' module."
            else:  # assert that self.render_with_user_info is being used
                assert "self.render(" not in python_contents, "The file " + f + \
                    " appears to be calling the self.render function. Please use self.render_with_user_info instead."


def test_endpoint_handlers_are_in_the_correct_file():
    """ Test that there are no EndpointHandlers in the user_interface file. """

    assert len([f for f in dir(user_interface) if "EndpointHandler" in f]
               ) == 0, "There is an EndpointHandler in the user_interface file. Please move this to json_api or github_collections."


def test_requirements_file_is_sorted():
    """
    Test whether requirements.txt is alphabetized (important to identify
    missing/redundant requirements)
    """

    with open('../requirements.txt') as f:
        lines = f.readlines()
    assert sorted(lines) == lines, "The requirements.txt file is not sorted."


def test_python_style_check():
    """ Test for PEP8 style """

    files_in_directory = os.listdir()
    for f in files_in_directory:
        if os.path.splitext(f)[1] == ".py":
            with open(f, "r") as python_file_handler:
                python_contents = python_file_handler.read()
                # compare the original file hash to the styled file hash
                styled_hash = hashlib.md5(
                    autopep8.fix_code(
                        python_contents, options={
                            'aggressive': 2}).encode()).hexdigest()
                original_hash = hashlib.md5(
                    python_contents.encode()).hexdigest()
                assert styled_hash == original_hash, "Style check failed on " + f + \
                    ". Run `autopep8 --in-place --aggressive --aggressive " + f + "`, or `autopep8 --in-place --aggressive --aggressive *.py`"


def test_search():
    """ Test that search results appear for a common search target """

    assert len(formatted_search("brain", 0)) > 0


def test_procfile():
    """ Assert that the Procfile points to a valid Python script. """

    with open("../Procfile", "r") as f:
        contents = f.read()
        filename = contents.replace(
            "web: python3 brainspell/",
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


@pytest.fixture
def app():
    """ Test that the Tornado application is successfully built. """
    return application


@pytest.mark.gen_test
def test_front_page(http_client, base_url):
    """ Test that the front page gives a 200 status code. """
    response = yield http_client.fetch(base_url)
    assert response.code == 200
