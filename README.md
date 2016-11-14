# brainspell-neo
Working on a new version on Brainspell. Experimenting with different stacks and setting up the JSON API with Postgres.

Clients can make requests to the JSON API directly, or access Brainspell through the web interface. A running Heroku instance is available at https://brainspell.herokuapp.com/.

=================================================

To run Brainspell locally:  
1) Clone the Git repo.  
2) Install the Python dependencies with `pip install -r requirements.txt`.  
3) Add the environment variable `DATABASE_URL`:  
`export DATABASE_URL="postgres://yaddqlhbmweddl:SxBfLvKcO9Vj2b3tcFLYvLcv9m@ec2-54-243-47-46.compute-1.amazonaws.com:5432/d520svb6jevb35"`

Now you can run Brainspell with `python3 json_api/main.py`. Brainspell should be running at `http://localhost:5000`.

================================================

![potential-configuration](https://cloud.githubusercontent.com/assets/7029855/19992170/d2a514dc-a1f8-11e6-94bc-f26eb1c4840d.png)
