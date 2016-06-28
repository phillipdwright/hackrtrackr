from flask import Flask
from flask import g, render_template, render_template_string, request
import os
import re
from helpers import keyword_check_comments_np_array, \
DATE_LIST, number_comments_per_month, get_matching_comments, COLORS, np
from hn_search_api_helpers import COMMENTS_FILE, load_json_file
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.models import NumeralTickFormatter

app = Flask(__name__)

# @app.context_processor
# def inject_renderer():
#     return dict(render_template_string=render_template_string)

@app.before_request
def before_request():
    # right now reading in json file but replace this with database
    g.comments = load_json_file(COMMENTS_FILE)
    
    # we could put stuff here about checking if json database is up-to-date

@app.route('/', methods = ['GET','POST'])
def index():

    if request.method == 'POST':
        
        # Get the entered keywords
        keywords = request.form["keywords"]
        # keywords = [keyword.strip() for keyword in keywords.split(',')]
        keywords = [word for word in re.split('\W+', keywords) if len(word) > 0]
        
        # Build an array of total comments
        total_counts_array = number_comments_per_month(g.comments)
        fig = figure(
            x_axis_type = "datetime",
            # plot_height = 600,
            # I'd like to use this responsive option, to scale the plot better,
            #  but it's only available in version 0.12, which hasn't been
            #  released yet:
            # responsive = 'box', 
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
        
        # get counts for the keyword, normalize by total counts
        for keyword, color in zip(keywords, COLORS):
            counts = keyword_check_comments_np_array(g.comments, keyword)
            counts /= total_counts_array

            fig.circle(DATE_LIST, counts, color=color, alpha=0.2, size=4)
            window_size = 3
            window=np.ones(window_size)/float(window_size)
            counts_avg = np.convolve(counts, window, 'same')

            # lose the first and last elements due to boundary effect
            fig.line(
                DATE_LIST[1:-1],
                counts_avg[1:-1],
                line_width=4,
                color=color,
                legend=keyword.title()
            )
        
        # Build the bokeh plot resources
        # https://github.com/bokeh/bokeh/tree/master/examples/embed/simple
        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()
        script, div = components(fig, INLINE)
        
        # Get recent comments matching the keywords
        recent_comments = get_matching_comments(g.comments, keywords)
        
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