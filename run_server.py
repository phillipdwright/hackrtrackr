from flask import Flask, g, render_template, render_template_string, request

import os
import re
import sqlite3

from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.models import NumeralTickFormatter

from helpers import \
DATE_LIST, number_comments_per_month, get_matching_comments, COLORS, np, \
get_matching_comments_db, keyword_check_db, plot_dots_and_line, make_fig
from hn_search_api_helpers import COMMENTS_FILE, CACHED_COUNTS_FILE, load_json_file


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
        
        # cached_counts_json = load_json_file(CACHED_COUNTS_FILE) # has both keyword counts and total counts
        # cached_counts = {}
        # for entry in cached_counts_json:
        #     cached_counts[entry['keyword']] = entry['counts']
        
        # Get the entered keywords
        keywords = request.form["keywords"]
        keywords = [keyword.strip() for keyword in keywords.split(',') if len(keyword) > 0]
        keywords = keywords[:len(COLORS)] # prevent too many keywords
        # keywords = [keyword.strip() for keyword in keywords.split(',') if len(keyword) > 0]
        # keywords = keywords[:len(COLORS)] # prevent too many keywords
        fig = make_fig(keywords)
        '''
        fig = figure(
            x_axis_type = "datetime",
            responsive = True,
            toolbar_location = None
        )
        
        # Formatting features that yield a pretty chart
        fig.xaxis.axis_line_color = fig.yaxis.axis_line_color = None
        fig.yaxis.minor_tick_line_color = fig.outline_line_color = None
        fig.xgrid.grid_line_color = fig.ygrid.grid_line_color = '#e7e7e7'
        fig.xaxis.major_tick_line_color = fig.yaxis.major_tick_line_color = '#e7e7e7'
        fig.legend.border_line_color = '#e7e7e7'
        fig.yaxis[0].formatter = NumeralTickFormatter(format="0%")
        
        # Repeat the color list as needed; this depends on Py2 integer division
        # COLORS = COLORS * ((len(keywords)-1) / len(COLORS) + 1)
        
        # if no keywords get total posts per month
        # should move redundant code into a new function...
        if not keywords:
            fig.yaxis[0].formatter = NumeralTickFormatter(format="0,0")
            counts = np.array(cached_counts['Total Counts'])
            fig = plot_dots_and_line(fig, counts, 'All', COLORS[0])
            
            # fig.circle(DATE_LIST, counts, color=COLORS[0], alpha=0.2, size=4)
            # window_size = 3
            # window=np.ones(window_size)/float(window_size)
            # counts_avg = np.convolve(counts, window, 'same')
            
            # # lose the first and last elements due to boundary effect
            # fig.line(
            #     DATE_LIST[1:-1],
            #     counts_avg[1:-1],
            #     line_width=4,
            #     color=COLORS[0],
            #     legend=keyword.title()
            # )
            
        # get counts for the keyword, normalize by total counts
        for keyword, color in zip(keywords, COLORS):
            # would it be faster to check all keywords for each comment
            # instead of doing one keyword at a time through all comments?
            # counts = keyword_check_comments_np_array(g.comments, keyword)
            # counts /= number_comments_per_month(g.comments)
            cached_keywords = cached_counts.keys()
            cached_keywords = [i.lower() for i in cached_keywords]
            
            if keyword.lower() in cached_keywords:
                print 'got cached counts for {}'.format(keyword)
                counts = np.array(cached_counts[keyword.lower()])
            else:
                counts = keyword_check_db(g.db, keyword)
                #counts = keyword_check_comments_np_array(g.comments, keyword)
                counts /= np.array(cached_counts['Total Counts'])
            fig = plot_dots_and_line(fig, counts, keyword, color)
            # fig.circle(DATE_LIST, counts, color=color, alpha=0.2, size=4)
            # window_size = 3
            # window=np.ones(window_size)/float(window_size)
            # counts_avg = np.convolve(counts, window, 'same')

            # # lose the first and last elements due to boundary effect
            # fig.line(
            #     DATE_LIST[1:-1],
            #     counts_avg[1:-1],
            #     line_width=4,
            #     color=color,
            #     legend=keyword.title()
            # )
        '''
        # Build the bokeh plot resources
        # https://github.com/bokeh/bokeh/tree/master/examples/embed/simple
        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()
        script, div = components(fig, INLINE)
        
        # Get recent comments matching the keywords
        recent_comments = get_matching_comments_db(g.db, keywords)
        if not keywords:
            keywords = ['All']
        print 'keywords = ',keywords
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