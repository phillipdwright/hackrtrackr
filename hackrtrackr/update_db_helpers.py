import sqlite3
from hn_search_api_helpers import get_thread_data_by_user, \
get_comments_from_thread, dump_json_file, call_api
from settings import DATABASE_NAME
import datetime
import re
from bs4 import BeautifulSoup
import sys
from finding_location import check_line_for_location, check_comment_for_location
import geocoder
import time
'''
Functions that are used for updating the DB
'''

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
    print 'In get_logo to download the logo {} for glassdoor id {}'.format(url, glassdoor_id)
    return True
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
 
    url_suffix = url.split('.')[-1]
    # *** NOT SURE HOW THIS FILE SYSTEM WILL BE ***
    img_filename = '/img/logos/{}.{}'.format(glassdoor_id, url_suffix)
    if os.path.isfile(img_filename):
        return True # already got that image
    
    with open(img_filename,'wb') as FH:
        FH.write(requests.get(url, headers=headers).content)
        #print 'Wrote {}'.format(img_filename)
    
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
        print 'Glassdoor match to {}'.format(glassdoor_data['name'])
        # see if there is already that ID in the company table
        # This is not best way to do it so fix this later...
        sql_command = 'SELECT Count(*) FROM company WHERE id == ?'
        cursor = db.execute(sql_command, (glassdoor_data['id'],))
        n_hits = cursor.fetchone()[0]
        if n_hits == 0:
            print 'It is not in the database so we would add it now'
            # we don't have it so add it to the company table
            # Use update_table from db_config
            # import the table company (make sure I don't have a company variable!)
            # send data as json of [{glassdoor_data}]
        else:
            print 'It was already in the database'
              
    return glassdoor_id
    
def geocode_locations(comment):
    '''
    given: comment with 'locations' key that is list of locations
    geocode each location and write them as rows to id_geocode table
    
    Suggestion for improvement - have a locations table in the database
    so we can look up common locations instead of geocoding them again
    Since a few cities are very common - San Francisco, New York, London
    '''
    unique_locations = [] # avoid adding multiples of same location
    locations = comment['locations']
    for location in locations:
        location = location.lower()
        
        tries = 2
        print location
        while tries < 10:
            g = geocoder.google(location)
            if any([g.city, g.state, g.country]):
                break
            time.sleep(tries)
            tries += 1
        if not any([g.city, g.state, g.country]):
            # Could not geocode - add to logger
            continue
        
        city, state, country = g.city, g.state, g.country
        if not city:
            city = ''
        if not state:
            state = ''
        if not country:
            country = ''
        d = dict(id=comment['id'],
                city=g.city, 
                state=g.state, 
                country=g.country, 
                latlng = g.latlng
            )
        if d not in unique_locations:
            unique_locations.append(d)
    
    for row in unique_locations:
        print 'Inserting {} {} into id_geocode'.format(row['id'], row['city'])
        # *** INSERT THIS LOCATION INTO THE ID_GEOCODE TABLE ***

    
def main_update():
    '''
    Main function for updating db
    '''
    #db = sqlite3.connect(DATABASE_NAME)
    # *** I'm confused about how to do database name stuff... need help with that ***
    db = sqlite3.connect('../test_db/testDB12.db')
    
    max_db_id = get_max_db_id(db)
    
    comments = get_current_month_comments()
    # [{id, thread_id, text, thread_date, comment_date}]
    
    new_comments = select_new_comments(comments, max_db_id)
    
    if new_comments:
        # compile this regex once since it is slow if compile it for each comment
        url_regex = re.compile('(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?', re.IGNORECASE)
    
    for comment in new_comments:
        company_guess = guess_company(comment)
        
        glassdoor_id = None
        if company_guess:
            comment_urls = get_urls(url_regex, comment)
            glassdoor_id = search_glassdoor(db, company_guess, comment_urls, stringency_flag = True)
            
        locations = check_comment_for_location(comment)
        
        comment['company'] = company_guess
        comment['glassdoor_id'] = glassdoor_id
        # *** WRITE [comment] to posts table here ***
        
        comment['locations'] = locations
        geocode_locations(comment)
        
        print 'Company guess: ',company_guess
        print 'Comment urls: ',comment_urls
        print 'Locations: ',locations
        print 'Glassdoor id: ',glassdoor_id
            
        r = raw_input()
        if r == 'q':
            sys.exit()
            
        #time.sleep(2) # to prevent too quick API calls
    
main_update()
