from flask import Flask, g, render_template, render_template_string, request

import os
import re
import sqlite3
import numpy as np
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8

from helpers import COLORS, get_matching_comments, make_fig

DATABASE = 'test_db/testDB12.db' # maybe put this in config file

app = Flask(__name__)

# @app.context_processor
# def inject_renderer():
#     return dict(render_template_string=render_template_string)

@app.before_request
def before_request():
    g.db = sqlite3.connect(DATABASE)
    # we could put stuff here about checking if json database is up-to-date

@app.route('/', methods = ['GET','POST'])
def index():

    if request.method == 'POST':
        # Get the entered keywords
        keywords = request.form["keywords"]
        keywords = [keyword.strip() for keyword in keywords.split(',') if len(keyword) > 0]
        keywords = keywords[:len(COLORS)] # prevent too many keywords

        fig = make_fig(keywords)
        
        # Build the bokeh plot resources
        # https://github.com/bokeh/bokeh/tree/master/examples/embed/simple
        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()
        script, div = components(fig, INLINE)
        
        # Get recent comments matching the keywords
        recent_comments = get_matching_comments(keywords)
        
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
    app.debug = True

    host = os.environ.get('IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    app.run(host=host, port=port)