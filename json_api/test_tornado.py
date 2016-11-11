import tornado.web
import os
import pytest
import main

application = main.make_app()

def test_procfile():
    import os
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