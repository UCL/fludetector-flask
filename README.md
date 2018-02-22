# fludetector

Website, REST API, and data processors for the fludetector service from UCL.

## Installation

This project requires:

- python 2.7
- virtualenv
- SQLite3
- lzop

You'll need to grab the project's secrets from someone, place them in a `.env` file in the project's root.
Something like this:

    $ cat .env
    GOOGLE_API_KEY=...
    ADMIN_USERNAME=...
    ADMIN_PASSWORD=...
    SECRET_KEY=...

This env file is where the sensitive data (e.g. API keys) live, they're not
committed to the repo.

Once you have those, clone this repo, point your terminal at it and run:

    $ ./scripts/init.sh

This will get most things sorted out for you. 

You can now run the server locally:

    $ ./scripts/serve.sh

Read the `init.sh` script to see what it's up to. There are also other scripts
in this directory that you might find useful.


## Making Changes

The project is a fairly standard Flask app, so if you know Flask, you know how
this works:

 - `fludetector/sources/` is where the data sources (e.g. Google, CSV, Twitter) are defined
 - `fludetector/static/` holds the static web assets (CSS, JS, images, etc.)
 - `fludetector/templates/` holds the HTML templates, written using the Jinaj2 template language
 - `fludetector/app.py` is where the Flask app is created and the routes/views are defined
 - `fludetector/forms.py` is where the WTForms forms are defined, for interacting with the user via HTML forms
 - `fludetector/models.py` is where the SQLAlchemy ORM models are defined, for interacting with teh SQLite3 database
 - `fludetector/scripts.py` holds the functions that are executed from the command line using `flask CMD`

### To the Database

If you need to change the database schema you should use SQLAlchemy and alembic.

Simply change the model definitions in `models.py` and then run:

    $ alembic revision -m 'DESCRIPTION OF CHANGES' --autogenerate

This will put a new migration file into `migrations/versions/`, read it over
to make sure it's doing what you expect. In particular you might need to
write some custom data migrations if you need to move data from other
tables/columns.

Once the migration file is ready, run it like this:

    $ alembic upgrade head

This will update your database to match your new schema. There's no need to
run this manually in production as the update script takes care of it for you.

### To the API

The API's code is found in `/fludetector/app.py`, the main functions are
prefixed with `api_`, for instance `api_scores` is the route function that
returns scores.

If you change the API, remember to update the docs page
`fludetector/templates/docs.html`.

### To the Templates

The templates are written using the Jinja2 template language. This means that
data can be passed in from the Python side of things and used to dynamically
create HTML.

If you need to add more data into a template, look for the route function in
`app.py` that renders the template file.

Most of the templates extend the base template, or the admin base template. If
you need to add a new JS/CSS dependency it's probably best to add it to the
base template, as that's where the `<head>` is defined.

### Deploying

There's a script in `scripts/` called `update.sh`, if you log into the
production machine, `cd` to the project's folder and run that script then
everything should be updated and deployed for you.

The update script pulls the latest changes from Gitlab. So don't make changes
directly to the code base in the prod machine, make them locally, push your
changes, then update to deploy them.


## TODO

[ ] Get the Twitter data source/analysis working again
[ ] Fix the update script so that the deploy user can restart the supervisor process for fludetector


## List of WTFs!

Recorded here for sanity.

### Listing models and regions

The home page has a list of the models and the regions that you can query over,
using checkboxes to select which ones to include in your graph.

Because we're rendering a list of regions for each model in a list of models,
we're using nested for loops in the jinja2 template.

Because we're interested in a list of the selected models and regions, we're
using a FieldList in the WTForms form.

Unfortunately, the FieldList demands that you order your fields like this
`model_regions-INDEX`. Getting hold of the index in the nested for loops is
tricky.

Hence the WTF in `home.html` where we use this hack: https://stackoverflow.com/questions/7537439/how-to-increment-a-variable-on-a-for-loop-in-jinja-template/32700975#32700975
to build a counter.
