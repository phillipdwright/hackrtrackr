from flask import Flask, g, render_template, render_template_string, request

import os
import re
import sqlite3
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8

from hackrtrackr.helpers import COLORS, get_matching_comments, make_fig,\
    get_matching_comments_2
# from helpers import COLORS, get_matching_comments, make_fig
from hackrtrackr import settings
import logging
import datetime

app = Flask(__name__)

# Configure the app
app.debug = settings.DEBUG
app.config['DATABASE'] = (0, settings.DATABASE_NAME)

# Make a custom logger so we don't log every GET request
logger = logging.getLogger('hn_logger')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('queries.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(module)s: %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)
#LOGGING_FORMAT = "%(asctime)s %(levelname)s %(module)s: %(message)s"
# set to warning to avoid all the _internal logs about eac
#logging.basicConfig(format=LOGGING_FORMAT, filename='queries.log', level=logging.WARNING)

def connect_db(db_name):
    # Connect to the database
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'][1])

@app.route('/', methods = ['GET','POST'])
def index():

    if request.method == 'POST':
        # Get the entered keywords
        keywords = request.form["keywords"]
        #keywords = [keyword.strip() for keyword in keywords.split(',') if len(keyword) > 0]
        keywords = [keyword.strip() for keyword in keywords.split(',') if len(keyword.strip()) > 0]
        keywords = keywords[:len(COLORS)] # prevent too many keywords
        
        # Get the location data
        user_location = (request.form['latitude'], request.form['longitude'])

        logger.info(', '.join(keyword for keyword in keywords))

        fig = make_fig(keywords)
        
        # Build the bokeh plot resources
        # https://github.com/bokeh/bokeh/tree/master/examples/embed/simple
        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()
        script, div = components(fig, INLINE)
        
        # Get recent comments matching the keywords
        recent_comments = get_matching_comments_2(keywords, user_location)
        
        # special case if no keywords entered - show 'All' comment counts
        if not keywords:
            keywords = ['All']

        # Build the web page
        html = render_template(
            'index.html',
            keywords = ', '.join(keyword.title() for keyword in keywords),
            plot_script=script,
            plot_div=div,
            js_resources=js_resources,
            css_resources=css_resources,
            jobs=recent_comments,
        )
        return html
    return render_template('index.html')
    
if __name__ == '__main__':

    host = os.environ.get('IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    app.run(host=host, port=port)