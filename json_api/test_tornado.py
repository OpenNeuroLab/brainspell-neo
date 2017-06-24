import tornado.web
import os
import pytest
import brainspell
import models
import search
import selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait


application = brainspell.make_app()


"""Configuring SauceLabs for Selenium Testing"""
capabilities = {}
username = os.environ["SAUCE_USERNAME"]
access_key = os.environ["SAUCE_ACCESS_KEY"]
capabilities["tunnel-identifier"] = os.environ["TRAVIS_JOB_NUMBER"]
hub_url = "%s:%s@localhost:4445" % (username, access_key)
capabilities["build"] = os.environ["TRAVIS_BUILD_NUMBER"]
capabilities["tags"] = [os.environ["TRAVIS_PYTHON_VERSION"], "CI"]
capabilities["browserName"] = "firefox"
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


# tests that the Tornado application is successfully built
@pytest.fixture
def app():
    return application

# tests that the base_url is returning a 200 code (good)
@pytest.mark.gen_test
def test_front_page(http_client, base_url):
    response = yield http_client.fetch(base_url)
    assert response.code == 200

