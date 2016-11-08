import tornado.web
import pytest

def func(x):
    return x + 1

def test_answer():
    assert func(3) == 4

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

application = tornado.web.Application([
    (r"/", MainHandler),
])

@pytest.fixture
def app():
    return application

@pytest.mark.gen_test
def test_hello_world(http_client, base_url):
    response = yield http_client.fetch(base_url)
    assert response.code == 200