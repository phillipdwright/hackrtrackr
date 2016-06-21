from flask import Flask
from flask import g, render_template, request
import os
from helpers import read_in_json_file, keyword_check_comments_np_array, DATE_LIST_STR

app = Flask(__name__)

@app.before_request
def before_request():
    g.data = read_in_json_file('all_comments.json')
    
    # we could put stuff here about checking if json database is up-to-date

@app.route('/', methods = ['GET','POST'])
def hello_world():

    if request.method == 'POST':
        keyword = request.form["keyword"]
        counts = keyword_check_comments_np_array(g.data, keyword)
        return render_template('index.html', DATE_LIST_STR = DATE_LIST_STR, counts = counts)
    return render_template('index.html')
    
if __name__ == '__main__':
    app.debug = True

    host = os.environ.get('IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    app.run(host=host, port=port)