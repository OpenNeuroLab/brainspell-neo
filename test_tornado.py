import tornado.web
import os
import pytest
import json_api.Tornado

application = json_api.Tornado.make_app()

@pytest.fixture
def app():
    return application

@pytest.mark.gen_test
def test_front_page(http_client, base_url):
    response = yield http_client.fetch(base_url)
    assert response.code == 200