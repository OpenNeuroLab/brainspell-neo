# brainspell-neo
Working on a new version on Brainspell.

Clients can make requests to the JSON API directly, or access Brainspell through the web interface. A running Heroku instance is available at https://brainspell.herokuapp.com/.

## Running Brainspell

To run Brainspell locally:  
1) Clone the Git repo.  
2) Install the Python dependencies with `pip install -r requirements.txt`.

Now you can run Brainspell with `python3 json_api/brainspell.py`. Brainspell should be running at `http://localhost:5000`.

## Code Organization

`json_api/brainspell.py` runs the Tornado main event loop and contains all of the RequestHandlers. Our naming convention is to use `____EndpointHandler` for handlers related to the JSON API, and `____Handler` for web interface handlers.  
`json_api/helper_functions.py` contains helper functions for adding articles to the database.  
`json_api/models.py` is for our ORM, PeeWee, which lets us treat our database like a Python object.  
`json_api/test_tornado.py` is our suite of continuous integration tests.  
`json_api/static/` contains the HTML, CSS, images, fonts, and Javascript code for the website.

Our Postgres database is hosted on Heroku. The full database is available in the `database_dumps` folder.

================================================

Former website for Brainspell: http://www.brainspell.org
