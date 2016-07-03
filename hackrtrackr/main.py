from flask import Flask, g, render_template, render_template_string, request

import os
import re
import sqlite3
import numpy as np
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8

from hackrtrackr.helpers import COLORS, get_matching_comments, make_fig
from hackrtrackr import settings

app = Flask(__name__)


app.debug = settings.DEBUG
app.config['SECRET_KEY'] = settings.SECRET_KEY
app.config['DATABASE'] = (0, settings.DATABASE_NAME)

def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'][1])
    # we could put stuff here about checking if json database is up-to-date

@app.route('/', methods = ['GET','POST'])
def index():

    if request.method == 'POST':
        # Get the entered keywords
        keywords = request.form["keywords"]
        keywords = [keyword.strip() for keyword in keywords.split(',') if len(keyword) > 0]
        keywords = keywords[:len(COLORS)] # prevent too many keywords
        
        # Get the location data
        user_location = (request.form['latitude'], request.form['longitude'])
        print 'Location: ', user_location # For testing purposes

        fig = make_fig(keywords)
        
        # Build the bokeh plot resources
        # https://github.com/bokeh/bokeh/tree/master/examples/embed/simple
        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()
        script, div = components(fig, INLINE)
        
        # Get recent comments matching the keywords
        recent_comments = get_matching_comments(keywords, user_location)
        
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