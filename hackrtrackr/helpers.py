import json
import copy
import datetime
import numpy as np
import calendar
import re
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from flask import g
from hn_search_api_helpers import COMMENTS_FILE, CACHED_COUNTS_FILE, load_json_file
from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import NumeralTickFormatter, HoverTool
import os.path
import vincenty
import collections


from hackrtrackr import settings
# import logging
# log = logging.getLogger(__name__)

# unicode errors with city names so used this SO answer:
# http://stackoverflow.com/questions/31137552/unicodeencodeerror-ascii-codec-cant-encode-character-at-special-name
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

KEYWORD_TO_REGEX = {
    'c':re.compile('(^|\W)(C)($|\W)'),
    'go':re.compile('(^|\W)(Go)($|\W)'),
    'objective-c':re.compile('(^|\W)(Objective-C|Objective C)($|\W)', re.IGNORECASE),
    'r':re.compile('(^|\W)(R)($|\W)'),
    'html':re.compile('(^|\W)(HTML|HTML5)($|\W)'),
    'css':re.compile('(^|\W)(CSS)($|\W)'),
    'frontend':re.compile('(^|\W)(Frontend|Front-end|Front end)($|\W)', re.IGNORECASE),
    'backend':re.compile('(^|\W)(Backend|Back-end|Back end)($|\W)', re.IGNORECASE),
    'remote':re.compile('(\W|^)(?<!no )(remote)(\W|$)', re.IGNORECASE), # ?<! is neg lookbehind
    'onsite':re.compile('(^|\W)(Onsite|On-site|On site)($|\W)', re.IGNORECASE),
    'internship':re.compile('(^|\W)(Intern|Interns|Internship|Internships)($|\W)', re.IGNORECASE),
    'full-time':re.compile('(^|\W)(Full time|Full-time|Fulltime)($|\W)', re.IGNORECASE),
    'visa':re.compile('(\W|^)(?<!no )(Visa|Visas)(\W|$)', re.IGNORECASE),
    'h1b':re.compile('(\W|^)(H1B|H1Bs)(\W|$)', re.IGNORECASE),
    'devops':re.compile('(\W|^)(DevOps|Dev-ops|Dev ops)(\W|$)', re.IGNORECASE),
    'san francisco':re.compile('(\W|^)(San Francisco|SF|Bay Area)(\W|$)', re.IGNORECASE),
    'new york':re.compile('(\W|^)(New York|NY|N\.Y\.C.|N\.Y\.)(\W|$)', re.IGNORECASE)
}

# Comment IDs that aren't real job posts so exclude them from being displayed
EXCLUDE_LIST = [
    11814917,
    11816723,
    11816728,
    11837035,
    11815029,
    11820450,
    11820467,
    11815098,
    11815422,
    12019764,
    12017045,
    12020411,
    12016831,
    12018381,
    12019415,
    12023654,
    12023852
    ]

KEYWORD_VARIANTS = [
    ('objective-c','objective c'),
    ('html','html5'),
    ('frontend','front-end','front end'),
    ('backend','back-end','back end'),
    ('onsite','on-site','on site'),
    ('internship','interns','intern','internships'),
    ('san francisco','sf','bay area'),
    ('new york','new york city','nyc','n.y.c','n.y.')]

# taken from here selecting 12, qualitative colors: http://colorbrewer2.org/
COLORS = (
        (0, 57, 230), # blue, saturated high 
        (239, 80, 47), # red-orange, saturated high 
        (250, 222, 40), # yellow, saturated high
        (84, 66, 142), # purple, saturated high
        (124, 178, 40), # green, saturated high
        (80, 117, 229), # blue, saturated low
        (239, 149, 131), # red-orange, saturated low
        (249, 233, 127), # yellow, saturated low
        (123, 115, 142), # purple, saturated low
        (149, 178, 101), # green, saturated low
    )
    
# HEX version because the rgb didn't seem to work well in <font color=> HTML tag
HEX_COLORS = ( 
    '#0039E6',
    '#EF502F',
    '#FADE28',
    '#54428E',
    '#7CB228',
    '#5075E5',
    '#EF9583',
    '#F9E97F',
    '#7B738E',
    '#95B265'
    )

# Filename for HN logo, used as default
HN_LOGO = os.path.join('img', 'logos', 'hn_logo.png')

# Base Glassdoor url
GD_BASE = 'https://www.glassdoor.com/Overview/-EI_IE{}.htm'

# Company logo files, and web file path for logos to be used by Flask
LOGO_FILE = os.path.join(settings.BASE_DIR, 'hackrtrackr', 'static', 'img', 'logos', '{}.png')
LOGO_IMG = os.path.join('img', 'logos', '{}.png')

def get_keyword_regex(keyword):
    '''
    given: keyword
    Looks to see if keyword matches a common term that has multiple spellings
    If so it will subsitute in a regex pattern that includes variants
    If not it will just return a regex pattern for the keyword excluding alpha-
    numerics on both sides
    Also the default here is to do IGNORECASE
    returns: regex pattern for keyword
    '''
    if keyword.lower() in KEYWORD_TO_REGEX:
        return KEYWORD_TO_REGEX[keyword.lower()]
    for variant in KEYWORD_VARIANTS:
        if keyword.lower() in variant:
            return KEYWORD_TO_REGEX[variant[0]] # first variant is key in dict
    
    escaped_keyword = re.escape(keyword)
    keyword_pattern = '(\W|^){}(\W|$)'.format(escaped_keyword)
    return re.compile(keyword_pattern, re.IGNORECASE)

def string_to_date(string_date):
    '''
    given: date as a string converts it to datetime.date
    '''
    return datetime.datetime.strptime(string_date, '%Y-%m-%d').date()

def get_date_list(date):
    '''
    Given a start date (datetime.date)
    Returns list of dates (YYYY-MM-DD) up to most recent month
    '''
    end_date = datetime.date.today().replace(day=1)
    date_list = []
    while date <= end_date:
        date_list.append(date)
        date += datetime.timedelta(days=calendar.monthrange(date.year, date.month)[1])
    return date_list

def build_date_objects():
    '''
    Creates and returns date objects for use in plots
    '''
    date_list = get_date_list(datetime.date(2011,4,1))
    # create a dict so we can quickly get the index for each date
    date_index = {date:index for index, date in enumerate(date_list)}
    date_list_str = [date.isoformat() for date in date_list]
    return date_list, date_index, date_list_str

_date_list, _date_index, _date_list_str = build_date_objects()
# DATE_LIST = get_date_list(datetime.date(2011,4,1))
# # create a dict so we can quickly get the index for each date
# DATE_INDEX = {date:index for index, date in enumerate(DATE_LIST)}
# DATE_LIST_STR = [date.isoformat() for date in DATE_LIST]
    
def plot_dots_and_line(fig, keyword, color):   
    '''
    given: fig for bokeh plot, keyword, total_counts, color
    gets the keyword counts for that keyword
    if keyword is '' that means no keywords were entered
    adds a dot and line plot of counts
    returns: fig
    '''
    
    total_counts, counts = keyword_counts(keyword)
    if keyword:
        normalized_counts = counts/ total_counts
        
        source = ColumnDataSource(
            data = {
                'x': _date_list,
                'y': normalized_counts,
                'keyword': [keyword.title()]*len(_date_list),
                'dates': _date_list_str,
                'total_jobs': total_counts,
                'matching_jobs' : counts
                }
            )
        
        tips = (
            ('Keyword','@keyword'),
            ('Date','@dates'),
            ('Total Jobs','@total_jobs'),
            ('Matching Jobs','@matching_jobs')
        )
        ordered_tips = collections.OrderedDict(tips)
    else:
        normalized_counts = total_counts
        source = ColumnDataSource(
            data = {
                'x': _date_list,
                'y': normalized_counts,
                'dates': _date_list_str,
                'total_jobs': normalized_counts,
                }
            )
            
        tips = (
            ('Date','@dates'),
            ('Total Jobs','@total_jobs')
        )
        ordered_tips = collections.OrderedDict(tips)

    dots = fig.circle('x','y',source=source, color=color, alpha=0.2, size=8)
    fig.add_tools(HoverTool(renderers=[dots], tooltips=ordered_tips))

    window_size = 3
    window=np.ones(window_size)/float(window_size)
    counts_avg = np.convolve(normalized_counts, window, 'same')
    
    #lose the first and last elements due to boundary effect
    fig.line(
        _date_list[1:-1],
        counts_avg[1:-1],
        line_width=4,
        color=color,
        legend=keyword.title()
    )
    
    return fig
    
def make_fig(keywords):
    '''
    given: list of keywords
    generates a bokeh fig with a dot and line graph of each keyword
    also deals with special case of no keywords to get total posts
    returns: fig
    '''
    and_or_keywords = [keyword for keyword in keywords if keyword[0] != '-']
    
    fig = figure(
            x_axis_type = "datetime",
            # responsive = True, # old responsive version, did not scale
            sizing_mode = 'stretch_both',
            tools="",
            toolbar_location = None
        )
        
    # Formatting features that yield a pretty chart
    fig.xaxis.axis_line_color = fig.yaxis.axis_line_color = None
    fig.yaxis.minor_tick_line_color = fig.outline_line_color = None
    fig.xgrid.grid_line_color = fig.ygrid.grid_line_color = '#e7e7e7'
    fig.xaxis.major_tick_line_color = fig.yaxis.major_tick_line_color = '#e7e7e7'
    fig.legend.border_line_color = '#e7e7e7'
    fig.yaxis[0].formatter = NumeralTickFormatter(format="0.0%")
    
    # if no keywords get total posts per month
    if not keywords:
        fig.yaxis[0].formatter = NumeralTickFormatter(format="0,0")
        fig = plot_dots_and_line(fig, '', COLORS[0])
     
    for keyword, color in zip(keywords, COLORS):
        # would it be faster to check all keywords for each comment
        # instead of doing one keyword at a time through all comments?
        # if we are doing html-> text for each comment I think so...
        fig = plot_dots_and_line(fig, keyword, color)
        
    return fig
    
def number_comments_per_month(comments):
    '''
    Returns np array of total # of comments per month
    '''
    
    counts = np.zeros(len(_date_list))
    
    for comment in comments:
        index = _date_index[comment['thread_date']]
        counts[index] += 1
    return counts
    
def keyword_counts(keyword):
    '''
    Used to get counts for how many comments had a hit to this keyword
    * Right now checks against html just so it is faster...
    '''
    
    if keyword and keyword[0] in ('+','-'):
        keyword = keyword[1:]
    sql_command = 'SELECT thread_date, text FROM posts'
    cursor = g.db.execute(sql_command)
    comments = cursor.fetchall()

    counts = np.zeros(len(_date_list))
    total_counts = np.zeros(len(_date_list))
    keyword_regex = get_keyword_regex(keyword)
        
    for comment in comments:
        text = comment[1]
        date = comment[0]
        try:
            index = _date_index[string_to_date(date)]
        except KeyError: # Not a good solution (not functional). Consider writing an update function called on KeyError.
            global _date_list, _date_index, _date_list_str
            _date_list, _date_index, _date_list_str = build_date_objects()
            
            # Reset the counts & total_counts values
            counts = np.zeros(len(_date_list))
            total_counts = np.zeros(len(_date_list))
            index = _date_index[string_to_date(date)]
        if keyword_regex.search(text):
            counts[index] += 1
        total_counts[index] += 1
    return total_counts, counts
    
def _get_pure_text(text):
    '''
    given: comment['text']
    return the pure_text
    doing this because our original pure_text method was combining two lines together
    '''
    soup = BeautifulSoup(text, "html.parser")
    pure_text = ''
    for pos, i in enumerate(soup.findAll('p')):
        pure_text += ' '.join(i.findAll(text=True)) + ' '
    return pure_text
    
def get_matching_comments(keywords, user_location):
    '''
    +keywords = AND must be present for match
    -keywords = NOT must be absent for match
    keywords  = OR  must have at least one present for match
    '''
    # Build a list of all comments posted from current month
    current_month = datetime.date.today().replace(day=1)
    
    sql_command = 'SELECT * FROM posts WHERE thread_date == ?'
    cursor = g.db.execute(sql_command, (current_month,))
    posts_names = [description[0] for description in cursor.description]
    recent_comments = cursor.fetchall()

    # Build a list of recent comments that match the keywords
    matching_comments = []
        
    # compile patterns for each keyword
    and_patterns = []
    not_patterns = []
    or_patterns = []
    patterns_in_order = [] # did this so they stay in same order to match color on plot
    for keyword in keywords:
        if keyword[0] == '+':
            keyword = keyword[1:]
            keyword_regex = get_keyword_regex(keyword)
            and_patterns.append(keyword_regex)
            patterns_in_order.append(keyword_regex)
        elif keyword[0] == '-':
            keyword = keyword[1:]
            keyword_regex = get_keyword_regex(keyword)
            not_patterns.append(keyword_regex)
        else:
            keyword_regex = get_keyword_regex(keyword)
            or_patterns.append(keyword_regex)
            patterns_in_order.append(keyword_regex)
    
    for comment_list in recent_comments:

        comment = {name:value for name,value in zip(posts_names,comment_list)}

        if comment['id'] in EXCLUDE_LIST:
            continue
        
        comment['pure_text'] = _get_pure_text(comment['text'])

        if keywords: # if no keywords just skip all this, we want to keep all comments
            
            if any(pattern.search(comment['pure_text']) for pattern in not_patterns):
                continue
            
            if not all(pattern.search(comment['pure_text']) for pattern in and_patterns):
                continue
            
            if or_patterns and not any(pattern.search(comment['pure_text']) for pattern in or_patterns):
                continue

        # if we got here it means it is a keeper!
        
        comment, total_keywords_found = _keyword_check(comment, patterns_in_order)
        
        # check whether remote or not
        remote = False
        p = re.compile('(\W|^)(?<!no )(remote)(\W|$)', re.IGNORECASE)
        if p.search(comment['pure_text']):
            remote = True
            comment['distance'] = 0
        else:
            comment['distance'] = _get_distance(comment['id'], user_location)
    
        location = _get_location(comment['id'], remote)
        
        if location:
            comment['location'] = location
            
        #comment['distance'] = _get_distance(comment['id'], user_location)
        
        # If company name is None then just grab the first part of the text
        if comment['company'] is None or comment['company'] == '':
            company_snippet = comment['pure_text'][:25] + '..'
        else:
            company_snippet = comment['company']
        comment['snippet'] = ' | '.join(i for i in (company_snippet, location) if i)
        
        if remote:
            comment['snippet'] += '<br>REMOTE'
        
        if comment['glassdoor_id']:
            # I need to fix the database so only the ones we have logos
            # for will have a squareLogo entry ***
            # Set logo from Glassdoor
            filename = LOGO_FILE.format(comment['glassdoor_id'])
            if os.path.isfile(filename):
                comment['logo'] = LOGO_IMG.format(comment['glassdoor_id'])
            else:
                comment['logo'] = HN_LOGO
            
            # Set url from Glassdoor
            comment['glassdoor_url'] = GD_BASE.format(comment['glassdoor_id'])
            
            # Get rating from Glassdoor
            comment['rating'] = _get_rating(comment)
            if not comment['rating']:
                del comment['rating']
                
            # Industry
            comment['industry'] = _get_industry(comment)
            if not comment['industry']:
                del comment['industry']
                
        else:
            # Use the generic HN logo if there is no Glassdoor match
            comment['logo'] = HN_LOGO
        
        # Append the comment to the matching comments list
        matching_comments.append(comment)
    
    if all(user_location):
        key = lambda comment: (comment['distance'], comment['comment_date'])
        reverse = False
    else:
        key = lambda comment: comment['comment_date']
        reverse = True
    
    # dave just adding this to force sort by date so I can check if the new
    # annotations are working or not...    
    key = lambda comment: comment['comment_date']
    reverse = True
    
    # Sort the matching comments starting with most recent and return the list
    matching_comments = sorted(
        matching_comments,
        key=key,
        reverse=reverse
    )
    
    return matching_comments

def _get_rating(comment):
    '''
    Query the company table for the company listed in the comment for its
    rating.  Return a dict of stars that represent what will be displayed on
    the job posting modal.
    '''
    id_ = comment['glassdoor_id']
    query = "SELECT overallRating FROM company WHERE id == ?"
    cursor = g.db.execute(query, (id_,))
    
    rating = cursor.fetchone()[0]

    if rating:
        # Get conservative integer estimates for each value
        stars = {
            'full': int(rating / 1),
            'half': 0,
            'empty': int((5 - rating) / 1)
        }
        
        # If the decimal portion of the rating is between 0.25 and 0.75, display
        #  a half-star.  Otherwise, round the rating to the nearest integer.
        remainder = rating % 1
        if remainder == 0:
            pass
        elif remainder < 0.25:
            stars['empty'] += 1
        elif remainder < 0.75:
            stars['half'] += 1
        else:
            stars['full'] += 1
        
        return stars
    return None
    
def _get_industry(comment):
    id_ = comment['glassdoor_id']
    query = "SELECT industry FROM company WHERE id == ?"
    cursor = g.db.execute(query, (id_,))
    return cursor.fetchone()[0]
    
def _get_location(id_, remote):
    '''
    given: comment id 
    returns: a string representation of the location (can be '')
    '''
    sql_command = 'SELECT * FROM id_geocode WHERE id == ?'
    cursor = g.db.execute(sql_command, (id_,))
    locations_names = [description[0] for description in cursor.description]
    locations = cursor.fetchall()
    # [('city', 'country', 'id', 'lat', 'lng', 'state')]
    
    if len(locations) > 1:
        location = 'Various sites'
    elif len(locations) == 0 and remote:
        location = 'Remote only'
    elif len(locations) == 0 and not remote:
        location = ''
    else:
        location_dict = {name:value for name,value in zip(locations_names,locations[0])}
        city = location_dict['city']
        state = location_dict['state']
        country = location_dict['country']
        
        if country in ('US','CA'):
            location = ', '.join(i for i in (city, state) if i)
            if not location:
                location = country
        else:
            location = ', '.join(i for i in (city, country) if i)

    return location
    
def _keyword_check(comment, patterns):
    '''
    given: comment dict and list of re patterns
    finds all pattern matches and adds html font color tags
    returns: comment dict and also total_keywords_found
    '''
    # get the dates as datetime.dates for the plot
    comment['thread_date'] = string_to_date(comment['thread_date'])
    comment['comment_date'] = string_to_date(comment['comment_date'])
    
    total_keywords_found = 0
    marked_text = comment['text'] # used to add the keyword highlighting

    for pattern, color in zip(patterns, HEX_COLORS):
        keyword_found = False
        start_ends = [] # store the position of each keyword match
        if pattern.search(comment['pure_text']):
            for m in pattern.finditer(marked_text):
                keyword_found = True # hmmm shouldn't this go after line 679?...
                start_ends.append((m.start(), m.end()))
        if keyword_found:
            total_keywords_found += 1
            
        # go in reverse to add the highlighting tags so the tags don't affect other positions
        for start_end in start_ends[::-1]:
            start, end = start_end
            
            # Phil's very clever solution to avoid marking inside <a href> tags!
            previous_text = marked_text[:start].split()
            if previous_text and previous_text[-1].startswith('href'):
                continue

            # regex picks up 1 char on both sides so adjust for that
            if start > 0: # make sure hit wasn't at beginning of line
                start += 1
            if end < len(marked_text) -1: # same with end of line
                end -= 1

            # insert the highlighting tags
            # can't use string.format() here because it will change
            # the length of special chars like quotes!
            marked_text = marked_text[:start] + \
                        '<font color="{}">'.format(color) + \
                        marked_text[start:end] + \
                        '</font>' + \
                        marked_text[end:]
            
    comment['marked_text'] = marked_text
    return comment, total_keywords_found
    
def _get_distance(id_, user_latlng):
    '''
    given: comment id and user latlng tuple
    calculates distance to all locations for that comment id
    returns: the closest distance
    '''
    if not all(user_latlng):
        return 25000

    user_latlng = tuple(float(i) for i in user_latlng)
    
    sql_command = 'SELECT lat, lng FROM id_geocode WHERE id == ?'
    cursor = g.db.execute(sql_command, (id_,))
    locations_names = [description[0] for description in cursor.description]
    locations = cursor.fetchall()
    # [('lat', 'lng')]
    
    closest_distance = 25000
    for job_latlng in locations:
        distance = vincenty.vincenty(user_latlng, job_latlng, miles=True)
        if distance < closest_distance:
            closest_distance = distance
    return closest_distance
