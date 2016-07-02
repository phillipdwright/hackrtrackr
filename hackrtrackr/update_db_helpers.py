import sqlite3
from hn_search_api_helpers import get_thread_data_by_user, \
get_comments_from_thread, dump_json_file
from settings import DATABASE_NAME
import datetime
'''
Functions that are used for updating the DB
'''

def get_highest_db_id():
    '''
    returns: highest id from the posts table
    '''
    #db = sqlite3.connect(DATABASE_NAME)
    db = sqlite3.connect('../test_db/testDB12.db')
    
    sql_command = 'SELECT MAX(id) FROM posts'
    cursor = db.execute(sql_command)
    max_id = cursor.fetchone()[0]
    return max_id
    
def get_current_month_comments():
    '''
    first gets Who is Hiring? thread from current month
    returns: a json (list of dicts) of that thread's comments
    '''
    current_date = datetime.date.today().replace(day=1)
    current_date_iso = current_date

    threads = get_thread_data_by_user('whoishiring')
    for thread in threads:
        if thread['created'] == current_date_iso:
            current_thread = thread
            break
    else:
        raise KeyError('Current month thread not found')
    
    comments = get_comments_from_thread(thread)
    return comments
    
    
def main_update():
    '''
    Main function for updating db
    '''
    highest_db_id = get_highest_db_id()
    
    comments = get_current_month_comments()
    # [{id, thread_id, text, thread_date, comment_date}]
    
    dump_json_file(comments, 'July_2016_comments.json')
    
    # best guess at company name and location
    
    # get google location data
    
    # get glassdoor data
    
    # update databases
    

main_update()
