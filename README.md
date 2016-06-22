# HackrTrackr

Hacker News is a social news site focused on computer science and entrepreneurship. Since 2011 there have been monthly “Who is Hiring” threads where hundreds of companies post descriptions of job openings. HackrTrackr allows a user to access the entire history of these job posts and to filter for just the jobs that match their interest. HackrTrackr provides an interactive visualization to see how job trends have changed over time. HackrTrackr also integrates company reviews from Glassdoor to enhance the user’s job search.

## Running Locally

Make sure you have Python [installed properly](http://install.python-guide.org).  Also, install the [Heroku Toolbelt](https://toolbelt.heroku.com/) and [Postgres](https://devcenter.heroku.com/articles/heroku-postgresql#local-setup).

```sh
$ git clone git@github.com:heroku/python-getting-started.git
$ cd python-getting-started

$ pip install -r requirements.txt

$ createdb python_getting_started

$ python manage.py migrate
$ python manage.py collectstatic

$ heroku local
```

Your app should now be running on [localhost:5000](http://localhost:5000/).

## Deploying to Heroku

```sh
$ heroku create
$ git push heroku master

$ heroku run python manage.py migrate
$ heroku open
```
or

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)

## Documentation

For more information about using Python on Heroku, see these Dev Center articles:

- [Python on Heroku](https://devcenter.heroku.com/categories/python)
