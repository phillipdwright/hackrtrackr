import sqlite3
from hn_search_api_helpers import get_thread_data_by_user, \
get_comments_from_thread, call_api
from settings import DATABASE_NAME
import datetime
import re
from bs4 import BeautifulSoup
from finding_location import check_line_for_location, check_comment_for_location
import geocoder
import time
#from main import app, connect_db
import logging
from operator import itemgetter
import os
import requests

from dbutils.db_config import update_table
from dbutils.setup_db import posts, company, id_geocode
#from db_config import update_table
from hackrtrackr import settings

# following should probably not be used... but maybe it's okay
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
'''
Functions that are used for updating the DB
'''

current_month = datetime.date.today().strftime('%b_%Y')
LOGGING_FILENAME = 'db_update_{}.log'.format(current_month)
LOGGING_FORMAT = "%(asctime)s %(levelname)s: %(message)s"
logging.basicConfig(format=LOGGING_FORMAT, filename=LOGGING_FILENAME, level=logging.DEBUG)

IMAGE_FILE_BASE = os.path.join(settings.BASE_DIR, 'hackrtrackr', 'static', 'img', 'logos', '{}.{}')

DATABASE_FILE = settings.DATABASE_NAME # Use this in production
#DATABASE_FILE = '/home/ubuntu/workspace/hackrtrackr-test/test_db/test_autoupdate.db'
def get_max_db_id(db):
    '''
    given: database connection
    returns: max id from the posts table
    '''
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

    threads = get_thread_data_by_user('whoishiring')
    for thread in threads:
        if thread['created'] == current_date:
            current_thread = thread
            break
    else:
        logging.error('Current month thread not found')
        raise KeyError('Current month thread not found')
    
    comments = get_comments_from_thread(thread)
    return comments
    
def select_new_comments(comments, max_db_id):
    '''
    given: comments and max_db_id
    returns: comments that have higher id than max_db_id, sorted oldest->newest
    '''
    new_comments = []
    for comment in comments:
        if comment['id'] > max_db_id:
            new_comments.append(comment.copy())
            
    sorted_new_comments = sorted(new_comments, key=itemgetter('id'))
    # for comment in sorted_new_comments:
    #     print comment['id'],
    return sorted_new_comments
    
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
        
    # first_line = soup.findAll('p')[0]
    # first_line = ' '.join(first_line.findAll(text=True))
    first_line = 'Comment has no text!'
    for soup_line in soup.findAll('p'):
        text_line = ' '.join(soup_line.findAll(text=True))

        if re.search('\w',text_line):
            first_line = text_line
            break
    
    if not first_line:
        return None
    
    # added spaces around - to avoid hyphenated words    
    if '|' not in first_line and ' - ' not in first_line:
        return None
    
    # first choice for delimiter is |
    # if not then try hyphen with spaces around it - this is used less often
    
    if '|' in first_line:
        delimeter = re.compile('\|')
    else:
        delimeter = re.compile(' - ')
    sections = delimeter.split(first_line)
    
    job_descriptors = re.compile('(^|\W)(Engineer|Senior|Developer|Onsite|Fulltime|Backend|Product Designer|Full Time)($|\W)', re.IGNORECASE)
    opener = re.compile('[\w \.]+')

    company_guess = None
    for section in sections:
        
        # this idea is we don't want the section for a company guess if it 
        # is really a location. However, we can't just check if part of the section
        # matches a location because there are companies like 'The New York Times'
        # So my way was to see if a section completely matches a location and 
        # if so skip it
        # However if the first section was like San Francisco and New York the
        # and would still pop up as the company... I guess you could say if there
        # are multiple locations found skip it... but then there are cased like
        # The Los Angeles Angels of Anaheim... 
        loc_line, possible_locs = check_line_for_location(section)
        if len(loc_line.strip()) == 0:
            continue
        #elif possible_locs and len(possible_locs) > 1:
        #    continue
        elif job_descriptors.search(section):
            continue
        
        m = opener.match(section) # match to make it be start of section
        if m:
            company_guess = m.group().strip()
    
            loc_line, possible_locs = check_line_for_location(company_guess)
            #print 'loc line = ',loc_line
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
                else: # we have a company guess, otherwise it will keep looping through sections
                    # case where there was http or https after company name
                    if split_company[-1] in ('http','https'):
                        company_guess = ' '.join(split_company[:-1])
                    break
    return company_guess
    
def get_urls(url_regex, comment):
    '''
    given: comment
    returns: list of all urls by regex match
    '''
    urls = []
    soup = BeautifulSoup(comment['text'])
    lines = soup.findAll(text=True)
    for line in lines:
        for m in url_regex.finditer(line):
            if m.group(2) not in urls:
                urls.append(m.group(2))
    return urls

def compare_urls(url1, url2):
    '''
    given: 2 urls
    checks if they match
    also will call a match if they include the same word longer than 3 letters and
    also have the same suffix (ie .com or .org, etc)
    returns: boolean
    '''
    if len(url1) == 0 or len(url2) == 0:
        return False
        
    # complete match
    if url1 == url2:
        return True

    # remove prefix stuff and look for a match
    url1 = url1.replace('http://','')
    url2 = url2.replace('http://','')
    url1 = url1.replace('www.','')
    url2 = url2.replace('www.','')
    if url1 == url2:
        return True
        
    # more relaxed - look for any word > 3letters matching, but the .com end has to match
    url1_set = set(url1.split('.')[:-1])
    url2_set = set(url2.split('.')[:-1])
    if url1.split('.')[-1] == url2.split('.')[-1]:
        intersection = url1_set & url2_set
        for item in intersection:
            if len(item) > 3:
                return True
    return False
    
def get_glassdoor_fields(employer):
    '''
    given: an employer from glassdoor api
    returns: dict with id, name, numberOfRatings, website, overallRating, 
    industry, squareLogo
    '''
    id = employer['id']
    name = employer['name']
    numberOfRatings = employer['numberOfRatings']
    website = None
    overallRating = None
    industry = None
    squareLogo = None
    
    if 'overallRating' in employer and numberOfRatings > 1:
        overallRating = employer["overallRating"]
    if 'industry' in employer:
        industry = employer['industry']
    if 'website' in employer:
        website = employer['website']
    if 'squareLogo' in employer and employer['squareLogo']:
        squareLogo = employer['id']
        get_logo(employer['id'], employer['squareLogo'])
        
    return dict(id=id,
        name=name,
        website=website,
        overallRating=overallRating,
        numberOfRatings=numberOfRatings,
        industry=industry,
        squareLogo=squareLogo,
        )
        
def get_logo(glassdoor_id, url):
    '''
    given: glassdoor_id and squareLogo url to the logo on glassdoor's site
    if we don't already have the url then download it
    '''
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
 
    url_suffix = url.split('.')[-1]
    
    img_filename = IMAGE_FILE_BASE.format(glassdoor_id, url_suffix)
    if os.path.isfile(img_filename):
        logging.info('Image file {} already exists'.format(img_filename))
        return # already got that image
    
    with open(img_filename,'wb') as FH:
        FH.write(requests.get(url, headers=headers).content)
        logging.info('Image file {} was created'.format(img_filename))
    
def search_glassdoor(db, company_guess, urls, stringency_flag = True):
    '''
    given: db, a guess for the company name, and urls from comment text
    searches glassdoor API and looks for match
    If stringency_flag is True it will only take an exactMatch or website match
    (and it will prioritize the website match)
    If stringency_flag is False it will take the top hit even if it is not an 
    exactMatch
    returns a dict of 
    If there is a glassdoor match, it will write that info to the company table
    It will return glassdoor_id (None if no match found)
    '''
    
    api_url = 'http://api.glassdoor.com/api/api.htm?t.p=72730&t.k=kWVAIhFKJam&\
        userip=104.131.86.71&format=json&v=1&action=employers&q={}'.format(company_guess)
    # replace my local ip with server ip: 104.131.86.71
    data = call_api(api_url, timeout = 30, user_agent_flag = True)
    glassdoor_response = data['response']
    
    glassdoor_id = None
    records_found = glassdoor_response['totalRecordCount']
    exactMatch = False
    websiteMatch = False
    matches_agree = False
    matched_employer = None
    for pos, employer in enumerate(glassdoor_response['employers']):
        website = employer['website']
        
        # if there is an exactMatch it will always be first employer
        if employer['exactMatch'] == True:
            exactMatch = True  
            matched_employer = employer
            
        for url in urls:
            if compare_urls(url, website):
                matched_employer = employer
                websiteMatch = True
                if pos == 0 and exactMatch:
                    matches_agree = True
                break
                
        if websiteMatch: # no need to keep searching after website match
            break
    
    # return top hit if stringency_flag is False
    if not stringency_flag and records_found > 0:
        glassdoor_data = get_glassdoor_fields(employer[0])
        
    # now get the data from the employer if there was a match
    if matched_employer:
        glassdoor_data = get_glassdoor_fields(matched_employer)
        glassdoor_id = glassdoor_data['id']
        
        # log_string = ''
        # for key in sorted(glassdoor_data):
        #     log_string += '\n{}: {}'.format(key, glassdoor_data[key])
        # logging.info('Made a glassdoor match:{}'.format(log_string))
        
        logging.info('Made a glassdoor match: glassdoor_id = ({})'.format(glassdoor_id))
        
        insert_row_into_table(db, 'company', glassdoor_data['id'], [glassdoor_data], 'id')
    return glassdoor_id
    
def geocode_locations(db, comment):
    '''
    given: comment with 'locations' key that is list of locations
    geocode each location and write them as rows to id_geocode table
    
    Suggestion for improvement - have a locations table in the database
    so we can look up common locations instead of geocoding them again
    Since a few cities are very common - San Francisco, New York, London
    '''
    #print 'Entering geocode_locations'
    unique_locations = [] # avoid adding multiples of same location
    locations = comment['locations']
    first_flag = True
    for location in locations:
        if first_flag:
            first_flag = False
        else:
            time.sleep(2)
        location = location.lower()
        
        tries = 0
        while tries < 5:
            g = geocoder.google(location)
            if any([g.city, g.state, g.country]):
                break
            time.sleep(2)
            tries += 1
        if not any([g.city, g.state, g.country]):
            logging.error('Could not geocode location: {}'.format(location))
            continue
        
        city, state, country = g.city, g.state, g.country
        if not city:
            city = ''
        if not state:
            state = ''
        if not country:
            country = ''
        lat, lng = g.latlng
        d = dict(id=comment['id'],
                city=g.city, 
                state=g.state, 
                country=g.country, 
                lat = lat,
                lng = lng
            )
        if d not in unique_locations:
            unique_locations.append(d)
    
    for row in unique_locations:
        # insert row data into id_geocode table
        insert_row_into_table(db, 'id_geocode', row['id'], [row], 'id')


def insert_row_into_table(db, table_name, id_, data_json, unique_column):
    '''
    given: table name, an id value that should not be in table, json data, and 
    the name of a column that should not have the id value
    first makes sure there are no rows with that id in the 'id' column
    then calls update_table to insert the row of data
    then checks the data is now in the table
    For the case of the id_geocode - there is no unique column so we will just
    add no matter what
    '''
    table_name_to_class = {'posts':posts, 'company':company, 'id_geocode':id_geocode}
    
    data_row = data_json[0]
    
    log_string = ''
    for key in sorted(data_row):
        if key == 'text':
            log_string += '\n{}: {}'.format(key, data_row[key][:80])
        else:
            log_string += '\n{}: {}'.format(key, data_row[key])
    logging.info('Data to insert into {}:{}'.format(table_name, log_string))
    
    # Ensure the column names match the keys in the data_json
    sql_command = 'SELECT * FROM {}'.format(table_name)
    cursor = db.execute(sql_command)
    col_names = [description[0] for description in cursor.description]
    if sorted(data_row) != sorted(col_names):
        msg = 'Data keys and column names from table {} do not match:\n'
        msg += 'Column names: {}\n'.format(sorted(col_names))
        msg += 'Data keys: {}'.format(sorted(data_row))
        logging.error(msg)
        raise KeyError('Col names and data keys do not match')
        
    
    sql_command = 'SELECT Count(*) FROM {} WHERE {} == ?'.format\
                (table_name, unique_column)
    cursor = db.execute(sql_command, (id_,))
    n_hits_before = cursor.fetchone()[0]
    if n_hits_before == 0 or table_name == 'id_geocode':
        conn = sqlite3.connect(DATABASE_FILE)
        update_table(table_name_to_class[table_name], data_json, setup = True, conn = conn)
        
        cursor = db.execute(sql_command, (id_,))
        n_hits_after = cursor.fetchone()[0]
        if n_hits_after == 1:
            logging.info('Added ({}) to {} table'.format(id_, table_name))
        elif n_hits_after == 0:
            logging.error('({}) was not added to {} table'.format(id_, table_name))
        else:
            if table_name == 'id_geocode':
                logging.info('Added ({}) to {} table'.format(id_, table_name))
                logging.info('There are now {} rows with this id'.format(n_hits_after))
            else:
                logging.error('Multiple copies of ({})\
                were added to {} table').format(id_, table_name)
    else:
        logging.info('({}) was already in the {} table'.format(id_, table_name))
    
def main_update():
    '''
    Main function for updating db
    '''
    logging.info('#################### Beginning main_update ####################')
    
    # *** I'm confused about how to do database name stuff... need help with that ***
    db = sqlite3.connect(DATABASE_FILE)
    
    max_db_id = get_max_db_id(db)
    logging.info('Max comment ID in database: {}'.format(max_db_id))
    
    comments = get_current_month_comments()
    # [{id, thread_id, text, thread_date, comment_date}]
    logging.info('Total comments found for the month: {}'.format(len(comments)))
    #print 'Number of current month comments = {}'.format(len(comments))
    
    new_comments = select_new_comments(comments, max_db_id)
    logging.info('New comments since last update: {}'.format(len(new_comments)))
    #print 'Number of new comments = {}'.format(len(new_comments))
    #sys.exit()
    
    if new_comments:
        # compile this regex once since it is slow if compile it for each comment
        url_regex = re.compile('(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?', re.IGNORECASE)
    
    for comment in new_comments:
        logging.info('#################### New comment ####################')
        company_guess = guess_company(comment)
        
        glassdoor_id = None
        if company_guess:
            logging.info('Guess made for company name: {}'.format(company_guess))
            comment_urls = get_urls(url_regex, comment)
            glassdoor_id = search_glassdoor(db, company_guess, comment_urls, stringency_flag = True)
        else:
            logging.info('No guess made for company name')
            
        locations = check_comment_for_location(comment)
        log_string = ''
        for location in locations:
            log_string += '\n{}'.format(location)
        logging.info('Following locations were found:{}'.format(log_string))
        
        comment['company'] = company_guess
        comment['glassdoor_id'] = glassdoor_id
        
        insert_row_into_table(db, 'posts', comment['id'], [comment], 'id')
        
        comment['locations'] = locations
        geocode_locations(db, comment)
            
        time.sleep(3) # to prevent too quick API calls
        
    logging.info('#################### Ending main_update ####################')
    db.close()
    
if __name__ == "__main__":
    main_update()
