import json
import requests
import re
import datetime
import copy
import os.path
import dateutil.parser

DATA_PATH = 'data/'
THREADS_FILE = os.path.join(DATA_PATH, 'threads.json')
COMMENTS_FILE = os.path.join(DATA_PATH, 'comments.json')
#COMMENTS_FILE = os.path.join(DATA_PATH, 'comments_db.json')
CACHED_COUNTS_FILE = os.path.join(DATA_PATH, 'keyword_counts_table.json')

# Next 4 functions are general json I/O stuff
def json_date_to_string(l):
    '''
    Given list of dicts
    Converts any datetime.date values to isoformat string
    Use so you can write out as json
    (Alternative is you could pass in as parameter which key(s) to convert)
    ... that might be better...
    '''
    l_with_str_dates = copy.deepcopy(l)
    for d in l_with_str_dates:
        for key,value in d.items():
            if type(value) == datetime.date:
                d[key] = value.isoformat()
    return l_with_str_dates
        
def json_string_to_date(l):
    '''
    Given list of dicts
    Converts any isoformat date fields from string to datetime.date
    Use if reading in json and want it as datetimes
    (Alternative is you pass in params of what key(s) to convert...)
    '''
    p = re.compile('\d{4}-\d{2}-\d{2}')
    l_with_dates = copy.deepcopy(l)
    for d in l_with_dates:
        for key,value in d.items():
            if type(value) == unicode and p.match(value) and len(value) == 10:
                d[key] = datetime.datetime.strptime(value, '%Y-%m-%d').date()
    return l_with_dates
    
def load_json_file(filename):
    '''
    given: json file
    converts any isoformat date fields from str to datetime.date
    returns: list of dicts
    '''
    with open(filename, 'r') as FH:
        json_data = json.load(FH)
    json_data = json_string_to_date(json_data)
    return json_data
    
def dump_json_file(list_dicts, filename):
    '''
    given: list of dicts and filename
    converts any datetime.date fields to isoformat str
    dumps to json file
    '''
    if os.path.isfile(filename):
        raise IOError('File {} already exists'.format(filename))
        
    list_dicts_str_converted = json_date_to_string(list_dicts)    
    with open(filename, 'w') as FH:
        json.dump(list_dicts_str_converted, FH)

# Code to handle API calls, taken from SWAPI project
class APIClientErrro(Exception):
    pass

def call_api(url, timeout = 30):
    try:
        resp = requests.request('GET', url, timeout=timeout)
    except requests.exceptions.ConnectionError:
        msg = 'Could not connect to the API at {}'.format(url)
        raise APIClientErrro(msg)
    except requests.exceptions.HTTPError:
        msg = 'Could not connect to API, got HTTPError'
        raise APIClientErrro(msg)
    except requests.exceptions.Timeout:
        msg = 'Could not connect to API, got Timeout'
        raise APIClientErrro(msg)

    if 400 <= resp.status_code < 500:
        msg = 'Request to API "{}" failed with status "{}". Reason: {}'
        msg = msg.format(url, resp.status_code, resp.text)
        raise APIClientErrro(msg)
    elif resp.status_code >= 500:
        msg = ('Request to API "{}" failed: '
               '500 Internal Server Error.').format(url)
        raise APIClientErrro(msg)

    try:
        data = json.loads(resp.content.decode('utf-8'))
    except ValueError:
        msg = ('Request to API "{}" returned JSON invalid data.'
               '').format(url)
        raise APIClientErrro(msg)
    return data

# Next four functions used for getting the 'Who is hiring?' thread IDs
def get_month_year_from_title(title):
    '''
    given: string like "Ask HN: Who is hiring? (November 2012)"
    returns: date object (Y, M D) with day set to 1
    '''
    p = re.compile('Ask HN: Who is hiring\? \(([a-z]+ \d+)\)', re.IGNORECASE)
    m = p.search(title)
    month_year = m.group(1)
    month_year_day = '{} 01'.format(month_year)
    
    # I want just a datetime.date and strptime gives datetime.datetime
    # so I convert it back to date() at the end of the line
    date = datetime.datetime.strptime(month_year_day, '%B %Y %d').date()
    return date  
    
def get_thread_data_by_user(username):
    '''
    given: username
    API search for hiring threads by that user
    filter out any that don't match exactly
    returns: list of dicts with parent_id and created keys
    '''  
    url_string = 'http://hn.algolia.com/api/v1/search?query=hiring?&tags=author_{},ask_hn&hitsPerPage=100'
    url = url_string.format(username)

    threads = []
    result = call_api(url)
    for hit in result['hits']:  
        if 'ask hn: who is hiring?' in hit['title'].lower():
            created = get_month_year_from_title(hit['title'])
            # note we could also used the 'created_at' or 'created_at_i' fields
            # but I feel using the title is fine
            d = dict(parent_id = int(hit['objectID']), created = created)
            threads.append(d)
    return threads
        
def all_hiring_threads():
    '''
    Searches HN API for threads by user whoishiring
    Also deals with a few months that were exceptions
    Returns: list of thread dicts
    '''
    threads = []
    for username in ('whoishiring', '_whoishiring'):
        threads += get_thread_data_by_user(username)
        
    # deal with the exception by user Aloisius from July 2011
    created = datetime.date(2011, 7, 1)
    exception_thread = dict(parent_id = 2719028, created = created)
    threads.append(exception_thread)
    
    # add the exception post from 2011-12 (ID = 3300290) by lpolovets
    created = datetime.date(2011, 12, 1)
    exception_thread = dict(parent_id = 3300290, created = created)
    threads.append(exception_thread)
    
    # remove the faulty 2011-12 post by whoishiring (ID = 3300371)
    try:
        threads.remove(dict(parent_id = 3300371, created = created))
    except ValueError:
        print('The faulty 2011-12 whoishiring post was not removed')
        
    return threads
    
def main_write_threads():
    '''
    Run this function to get IDs of all hiring threads, including 2 exceptions
    These will then be written to a file "data/threads.json"
    The json will have 2 fields - created and ID
    Note that there will be 2 separate threads for 2011-12
    '''
    threads = all_hiring_threads()
    dump_json_file(threads, THREADS_FILE)
    
# next 3 functions used for getting comments from threads
def convert_iso_8601_to_datetime(s):
    '''
    given: the comment 'created_at' is in iso_8601
    return: datetime.date
    '''
    dt = dateutil.parser.parse(s)
    return dt.date()
    
def get_comments_from_thread(thread):
    '''
    given: thread for a particular month
    Makes API call on that id
    gets text of each comment
    (we could get either ISO 8601 or UNIX time for comment - created_at_i for unixtime)
    returns: list of dicts for each comment
    '''
    url_string = 'http://hn.algolia.com/api/v1/items/{}'
    url = url_string.format(thread['parent_id'])
    result = call_api(url)
    
    comments = []
    for comment in result['children']:
        if 'text' in comment.keys() and len(comment['text']) > 0:
            comment_date = convert_iso_8601_to_datetime(comment['created_at'])
            comment_dict = dict(id = comment['id'], thread_id = thread['parent_id'],
                            text = comment['text'], thread_date = thread['created'],
                            comment_date = comment_date)
            comments.append(comment_dict)
    return comments
    
def main_write_comments(split_by_month_flag = False):
    '''
    given: threads filename that has IDs of all the threads
    get comments from each thread and then write those out to file(s)
    if the split_by_month_flag is True it will write out the comments
    to separate files for each month (files will be named YYYY-MM-DD.json)
    if False all the comments will just go to a single file
    '''
    threads = load_json_file(THREADS_FILE)
    
    comments = []
    for thread in threads:
        thread_comments = get_comments_from_thread(thread)
        if split_by_month_flag:
            filename = '{}.json'.format(thread['created'])
            dump_json_file(thread_comments, filename)
        else:
            comments += thread_comments
    if not split_by_month_flag:
        dump_json_file(comments, COMMENTS_FILE)
