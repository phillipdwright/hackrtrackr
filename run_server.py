from flask import Flask
from flask import g, render_template, request
import os
from helpers import read_in_json_file, keyword_check_comments_np_array, DATE_LIST, number_comments_per_month
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8

app = Flask(__name__)

@app.before_request
def before_request():
    g.comments = read_in_json_file('all_comments.json')
    
    # we could put stuff here about checking if json database is up-to-date

@app.route('/', methods = ['GET','POST'])
def hello_world():

    if request.method == 'POST':
        keywords = request.form["keywords"]

        keywords = keywords.split(',')
        total_counts_array = number_comments_per_month(g.comments)
        fig = figure(x_axis_type = "datetime")
        colors = ('red', 'blue', 'green', 'black')
        
        # get counts for the keyword, normalize by total counts
        for keyword, color in zip(keywords, colors):
            counts = keyword_check_comments_np_array(g.comments, keyword)
            counts /= total_counts_array
            #print counts
            fig.line(DATE_LIST, counts, color=color, legend=keyword)
        
        # some bokeh code I based of this example:
        # https://github.com/bokeh/bokeh/tree/master/examples/embed/simple
        
        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()
        script, div = components(fig, INLINE)
        html = render_template(
            'index.html',
            keywords = ' '.join(keywords),
            plot_script=script,
            plot_div=div,
            js_resources=js_resources,
            css_resources=css_resources,
        )
        return html
    return render_template('index.html')
    
if __name__ == '__main__':
    app.debug = True

    host = os.environ.get('IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    app.run(host=host, port=port)