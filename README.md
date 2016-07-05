# HackrTrackr

Hacker News is a social news site focused on computer science and entrepreneurship. Since 2011 there have been monthly “Who's Hiring” threads where hundreds of companies post descriptions of job openings. HackrTrackr allows a user to access the entire history of these job posts and to filter for just the jobs that match their interest. HackrTrackr provides an interactive visualization to see how job trends have changed over time. HackrTrackr also integrates company reviews from Glassdoor to enhance the user’s job search.

## Working with HackrTrackr Locally

To work with a local copy of HackrTrackr, you will need to have [Python 2.7](http://install.python-guide.org) installed.

Clone the repo

```sh
$ git clone git@github.com:phillipdwright/hackrtrackr.git
$ cd hackrtrackr
```

Install dependencies

```sh
$ pip install -r requirements.txt
```

Set up database

```sh
$ python hackrtrackr/initialize_data.py
$ python dbutils/setup_db.py
$ python hackrtrackr/update_db_helpers.py
```

## Contributors

* [Phil Wright](https://github.com/phillipdwright)
* [David Granas](https://github.com/duddles)
* [Greg Karpov](https://github.com/gkarp)