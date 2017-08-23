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

import selenium
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions


application = brainspell.make_app()


"""Configuring SauceLabs for Selenium Testing """


capabilities = {}
username = os.environ["SAUCE_USERNAME"]
access_key = os.environ["SAUCE_ACCESS_KEY"]
capabilities["tunnel-identifier"] = os.environ["TRAVIS_JOB_NUMBER"]
hub_url = "{0}:{1}@localhost:4445".format(username, access_key)
capabilities["build"] = os.environ["TRAVIS_BUILD_NUMBER"]
capabilities["tags"] = [os.environ["TRAVIS_PYTHON_VERSION"], "CI"]
capabilities["browserName"] = "firefox"
driver = webdriver.Remote(
    desired_capabilities=capabilities,
    command_executor="http://{0}/wd/hub".format(hub_url))


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

    DAO_VIOLATION = "You should not access the models directly in your handler. The file {0} should be rewritten to no longer import models, and instead use a layer of abstraction (so that we can reimplement our data access layer if needed)."
    UI_IN_WRONG_FILE = "The file {0} appears to render an HTML template. Please move this to the 'user_interface' module."
    WRONG_RENDER_FUNCTION = "The file {0} appears to be calling the self.render function. Please use self.render_with_user_info instead."

    files_to_enforce = [
        "json_api.py",
        "user_interface.py",
        "github_collections.py"]
    for f in files_to_enforce:
        with open(f, "r") as python_file_handler:
            python_contents = python_file_handler.read()
            # checks for ORM use in the wrong files
            assert ("from models import" not in python_contents) and ("import models" not in python_contents)  \
                and (".execute()") not in python_contents, DAO_VIOLATION.format(f)
            # checks that UI classes are in the correct file
            if f == "json_api.py" or f == "github_collections.py":
                assert "self.render" not in python_contents, UI_IN_WRONG_FILE.format(
                    f)
            # assert that self.render_with_user_info is being used
            else:
                assert "self.render(" not in python_contents, WRONG_RENDER_FUNCTION.format(
                    f)


def test_endpoint_handlers_are_in_the_correct_file():
    """ Test that there are no EndpointHandlers in the user_interface file. """
    ENDPOINT_IN_WRONG_FILE = "There is an EndpointHandler in the user_interface file. Please move this to json_api or github_collections."

    assert len([f for f in dir(user_interface) if "EndpointHandler" in f]
               ) == 0, ENDPOINT_IN_WRONG_FILE


def test_requirements_file_is_sorted():
    """
    Test whether requirements.txt is alphabetized (important to identify
    missing/redundant requirements)
    """
    UNSORTED_REQUIREMENTS_FILE = "The requirements.txt file is not sorted."

    with open('../requirements.txt') as f:
        lines = f.readlines()
    assert sorted(lines) == lines, UNSORTED_REQUIREMENTS_FILE


def test_python_style_check():
    """ Test for PEP8 style """

    STYLE_CHECK_FAILED = "Style check failed on {0}. Run `autopep8 --in-place --aggressive --aggressive {0}`, or `autopep8 --in-place --aggressive --aggressive *.py`"

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
                assert styled_hash == original_hash, STYLE_CHECK_FAILED.format(
                    f)


def test_search():
    """ Test that search results appear for a common search target """

    SEARCH_BROKEN = "A search for 'brain' is returning nothing."

    assert len(formatted_search("brain", 0)) > 0, SEARCH_BROKEN


def test_procfile():
    """ Assert that the Procfile points to a valid Python script. """

    PROCFILE_NOT_VALID = "The Procfile is referring to a file that doesn't exist."

    with open("../Procfile", "r") as f:
        contents = f.read()
        filename = contents.replace(
            "web: python3 brainspell/",
            "").replace(
            "\n",
            "")
        assert filename in os.listdir(), PROCFILE_NOT_VALID


def test_existence():  # Using selenium testing to verify existence of site elements
    driver.get("/")
    #driver.get("localhost:5000")
    driver.implicitly_wait(0.5)
    assert "Brainspell" in driver.title  # Checks website was correctly received

    # Ensuring elements of view article page are all present
    driver.get("https://brainspell.herokuapp.com/view-article?id=00000000")
    WebDriverWait(
        driver, 3).until(
        expected_conditions.presence_of_element_located(
            (By.CLASS_NAME, "dropbtn")))
    meshButtons = driver.find_elements_by_class_name("dropbtn")

    assert meshButtons, "Voting Buttons not included"
    table = driver.find_elements_by_class_name("experiment-table-row")
    assert table, "Experiments Table not Generated"

    buttons = driver.find_elements_by_class_name("dropbtn")
    buttons[0].click()
    WebDriverWait(
        driver, 3).until(
        expected_conditions.presence_of_element_located(
            (By.CLASS_NAME, "modal-body")))
    assert "modal-body" in driver.page_source
    driver.find_element_by_id("closer").click()

    # Evaluate search page
    driver.get("https://brainspell.herokuapp.com/search?q=brain&req=t")
    show_widgets = WebDriverWait(driver, 10).until(
        expected_conditions.element_to_be_clickable((By.ID, "widgetOption"))
    )
    show_widgets.click()
    assert show_widgets.value_of_css_property("display") == "none"

    # Evaluate whether 10 results are properly returned
    link = driver.find_elements_by_css_selector('[href^=view-article]')
    assert len(link) == 10, "10 search results were not found!"
    print("All cases passed")


@pytest.fixture
def app():
    """ Test that the Tornado application is successfully built. """
    return application


@pytest.mark.gen_test
def test_front_page(http_client, base_url):
    """ Test that the front page gives a 200 status code. """
    response = yield http_client.fetch(base_url)
    assert response.code == 200
