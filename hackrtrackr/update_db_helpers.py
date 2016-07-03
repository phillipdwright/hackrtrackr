import sqlite3
from hn_search_api_helpers import get_thread_data_by_user, \
get_comments_from_thread, dump_json_file, call_api
from settings import DATABASE_NAME
import datetime
import re
from bs4 import BeautifulSoup
import sys
from finding_location import check_line_for_location, check_comment_for_location
'''
Functions that are used for updating the DB
'''

def get_max_db_id():
    '''
    returns: max id from the posts table
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
    then gets the comments for that thread
    returns: comments as json list of dicts
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
    
def select_new_comments(comments, max_db_id):
    '''
    given: comments and max_db_id
    returns: comments that have higher id than max_db_id
    '''
    new_comments = []
    for comment in comments:
        if comment['id'] > max_db_id:
            new_comments.append(comment.copy())
    return new_comments
    
def guess_company(comment):
    '''
    given: comment
    Looks if first line has delimeters | or -
    If so it will search each section for a possible name
    For each section it gets text up to the first non-[A-z0-9.]
    The only heuristic I am using is that if a section completely matches 
    a location then I move on to the next section
    (Another possible heuristic I could use is that usually the company name 
    shows up in a url or email on the comment - but not always)
    If the possibly company name is longer than 10 words or shorter than 2 chars
    it will return None
    Otherwise returns guess for the company name
    
    Note - sometimes posts start with job position like Senior Engineer or 
    something... right now I would mistake these for company names
    '''

    soup = BeautifulSoup(comment['text'], "html.parser") 
        
    first_line = soup.findAll('p')[0]
    first_line = ' '.join(first_line.findAll(text=True))
    
    if not first_line:
        return None
    
    if '|' not in first_line and '-' not in first_line:
        return None
    
    delimeters = re.compile('[|-]')
    sections = delimeters.split(first_line)
    
    job_descriptors = re.compile('(^|\W)(Engineer|Senior|Developer|Onsite|Fulltime)($|\W)', re.IGNORECASE)
    opener = re.compile('[\w \.]+')
    company_guess = None
    for section in sections:
        
        m = opener.match(section) # match to make it be start of section
        if m:
            company_guess = m.group().strip()
    
            loc_line, possible_locs = check_line_for_location(company_guess)
        
            # ignore if it completely matches a location
            # loc_line has location replaced with spaces, so use strip to 
            # see if it is all spaces
            if possible_locs and len(loc_line.strip()) == 0:
                company_guess = None
            elif job_descriptors.search(section):
                company_guess = None
            else:
                split_company = company_guess.split()
                if len(split_company) >= 10:
                    company_guess = None
                elif len(company_guess) < 3:
                    company_guess = None
                break
    return company_guess
    
def get_urls(comment):
    '''
    given: comment
    returns: list of all urls by regex match
    '''
    
    urls = []
    soup = BeautifulSoup(comment['text'])
    lines = soup.findAll(text=True)
    for line in lines:
        for m in p.finditer(line):
            if m.group(2) not in urls:
                urls.append(m.group(2))
    return urls
    
def search_glass_door(company_guess, urls):
    '''
    given: a guess for the company name and urls from comment text
    searches glassdoor API and looks for exact match or url match
    returns a dict of 
    {
        glassdoor_id:
        industry:
        name:
        numberOfRatings:
        overallRating:
        squareLogo:
        website:
    }
    '''
    
    
def main_update():
    '''
    Main function for updating db
    '''
    max_db_id = get_max_db_id()
    
    comments = get_current_month_comments()
    # [{id, thread_id, text, thread_date, comment_date}]
    
    new_comments = select_new_comments(comments, max_db_id)
    
    if new_comments:
        # compile this regex once since it is slow if compile it for each comment
        url_regex = re.compile('(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?', re.IGNORECASE)
    
    
    for comment in new_comments:
        company_guess = guess_company(comment)
        
        if company_guess:
            comments_urls = get_urls(comment)
            
            
        
        locations = check_comment_for_location(comment)
        
        
        
        
    
    # best guess at company name and location
    
    # get google location data
    
    # get glassdoor data
        # - first get all urls in post to compare to glassdoor
    
    # update databases
    
    #dump_json_file(comments, 'July_2016_comments.json')
main_update()
