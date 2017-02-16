# brainspell-neo
Working on a new version on Brainspell.

Clients can make requests to the JSON API directly, or access Brainspell through the web interface. A running Heroku instance is available at https://brainspell.herokuapp.com/.

## Running Brainspell

To run Brainspell locally:  
1) Clone the Git repo.  
2) Install the Python dependencies with `pip install -r requirements.txt`.

Now you can run Brainspell with `python3 json_api/brainspell.py`. Brainspell should be running at `http://localhost:5000`.

## Code Organization

`json_api/brainspell.py` runs the Tornado main event loop.  
`json_api/models.py` is for our ORM, PeeWee, which lets us treat our database like a Python object.  
`json_api/test_tornado.py` is our set of continuous integration tests.  
`json_api/static/` contains the HTML, CSS, and Javascript code for the website.

Our database is hosted on Heroku. The full database is available in the `database_dumps` folder.

Potential stack in the future:

![potential-configuration](https://cloud.githubusercontent.com/assets/7029855/19992170/d2a514dc-a1f8-11e6-94bc-f26eb1c4840d.png)

Currently, we're using Tornado as our HTTP server rather than Nginx.

================================================

Former website for Brainspell: http://www.brainspell.org
