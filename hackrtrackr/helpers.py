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

# unicode errors with city names so used this SO answer:
# http://stackoverflow.com/questions/31137552/unicodeencodeerror-ascii-codec-cant-encode-character-at-special-name
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

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

BLUE = '#0039E6'
RED_ORANGE = '#EF502F'

# Filename for HN logo, used as default
HN_LOGO = os.path.join('img', 'logos', 'hn_logo.png')

# Base Glassdoor url
GD_BASE = 'https://www.glassdoor.com/Overview/-EI_IE{}.htm'

# Company logo files, and web file path for logos to be used by Flask
LOGO_FILE = os.path.join(settings.BASE_DIR, 'hackrtrackr', 'static', 'img', 'logos', '{}.png')
LOGO_IMG = os.path.join('img', 'logos', '{}.png')

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
    end_date = datetime.date(2016,7,1) # don't want july showing up in plot
    date_list = []
    while date <= end_date:
        date_list.append(date)
        date += datetime.timedelta(days=calendar.monthrange(date.year, date.month)[1])
        #date += datetime.timedelta(days=32)
        #date = date.replace(day=1)
    return date_list
    
DATE_LIST = get_date_list(datetime.date(2011,4,1))
# create a dict so we can quickly get the index for each date
DATE_INDEX = {date:index for index, date in enumerate(DATE_LIST)}
DATE_LIST_STR = [date.isoformat() for date in DATE_LIST]
    
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
                'x': DATE_LIST,
                'y': normalized_counts,
                'keyword': [keyword.title()]*len(DATE_LIST),
                'dates': DATE_LIST_STR,
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
                'x': DATE_LIST,
                'y': normalized_counts,
                'dates': DATE_LIST_STR,
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
        DATE_LIST[1:-1],
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
    # cached_counts_json = load_json_file(CACHED_COUNTS_FILE) # has both keyword counts and total counts
    # cached_counts = {}
    # for entry in cached_counts_json:
    #     cached_counts[entry['keyword']] = entry['counts']
    
    fig = figure(
            x_axis_type = "datetime",
            # responsive = True, # old responsive version, did not scale
            sizing_mode = 'stretch_both',
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
        '''
        cached_keywords = cached_counts.keys()
        cached_keywords = [i.lower() for i in cached_keywords]
        
        if keyword.lower() in cached_keywords:
            #print 'got cached counts for {}'.format(keyword)
            counts = np.array(cached_counts[keyword.lower()])
        else:
            counts = keyword_counts(keyword)
            counts /= np.array(cached_counts['Total Counts'])
        fig = plot_dots_and_line(fig, counts, keyword, color, cached_counts['Total Counts'])
        '''
        
    return fig
    
def number_comments_per_month(comments):
    '''
    Returns np array of total # of comments per month
    '''
    counts = np.zeros(len(DATE_LIST))
    
    for comment in comments:
        index = DATE_INDEX[comment['thread_date']]
        counts[index] += 1
    return counts
    
def keyword_counts(keyword, prefix_suffix_flag=True, case_flag=False):
    '''
    Used to get counts for how many comments had a hit to this keyword
    * Right now checks against html just so it is faster...
    '''
    sql_command = 'SELECT thread_date, text FROM posts'
    cursor = g.db.execute(sql_command)
    comments = cursor.fetchall()
    
    counts = np.zeros(len(DATE_LIST))
    total_counts = np.zeros(len(DATE_LIST))
    keyword = re.escape(keyword) # escape special regex characters
    #print keyword
    if prefix_suffix_flag:
        keyword = '(\W|^){}(\W|$)'.format(keyword) # so it can't be part of a larger word
    
    if case_flag:
        p = re.compile(keyword)
    else:
        p = re.compile(keyword, re.IGNORECASE)
        
    for comment in comments:
        text = comment[1]
        date = comment[0]
        index = DATE_INDEX[string_to_date(date)]
        if p.search(text):
            counts[index] += 1
        total_counts[index] += 1
    return total_counts, counts
 
def get_matching_comments(keywords, user_location):
    # Build a list of all comments posted from June 2016
    current_month = datetime.date.today().replace(day=1)
    current_month = datetime.date(2016,7,1).isoformat() # take this out if auto-update is working
    
    sql_command = 'SELECT * FROM posts WHERE thread_date == ?'
    cursor = g.db.execute(sql_command, (current_month,))
    posts_names = [description[0] for description in cursor.description]
    recent_comments = cursor.fetchall()

    # Build a list of recent comments that match the keywords
    matching_comments = []
        
    # compile patterns for each keyword
    patterns = []
    for keyword in keywords:
        keyword = re.escape(keyword)
        keyword = '(\W|^){}(\W|$)'.format(keyword)
        p = re.compile(keyword, re.IGNORECASE)
        patterns.append(p)
    
    for comment_list in recent_comments:
        comment = {name:value for name,value in zip(posts_names,comment_list)}
        comment['pure_text'] = BeautifulSoup(comment['text'], 'html.parser').get_text()
        comment, total_keywords_found = _keyword_check(comment, patterns)
        
        # Verify that all keywords are found in the comment 
        # (bug/feature - also works for 0 keywords)
        if total_keywords_found == len(keywords):
        
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
            if comment['company'] is None:
                company_snippet = comment['pure_text'][:25] + '..'
            else:
                company_snippet = comment['company']
            comment['snippet'] = ' | '.join(i for i in (company_snippet, location) if i)
            
            if remote:
                comment['snippet'] += '<br><font color="{}">REMOTE</font>'.format(RED_ORANGE)
            
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
    
    # Sort the matching comments starting with most recent and return the list
    matching_comments = sorted(
        matching_comments,
        key=key,
        reverse=reverse
    )
    
    return matching_comments    

def _get_snippet(text, keywords):
    '''
    Return a ten-word snippet from the job post containing the first
    keyword match
    
    Example for a search with keywords=['android']:
    "...Swift) * Got some Android chops too? That's a plus!..."
    '''
    ellipsis = '...'
    
    text_list = text.split()
    keywords = [keyword.lower() for keyword in keywords]
    
    # Start at the beginning of the post if for some reason
    match_position = 0
    
    for word in text_list:
        if any(keyword in word.lower() for keyword in keywords):
            match_position = text_list.index(word)
            break
    
    # Start pos. is at least 0 and at most 10 words before the end of the post
    start_position = min(max(0, match_position - 4), len(text_list) - 10)
    end_position = start_position + 10
    
    
    for word in text_list[start_position : end_position]:
        if 'http://' in word or 'https://' in word or 'www.' in word:
            text_list.remove(word)
    
    # Put the words around the keyword match back together
    snippet = ' '.join(text_list[start_position : end_position])
    
    # Put an ellipsis at the beginning and end of the snippet, as appropriate
    if start_position > 0:
        snippet = u'{}{}'.format(ellipsis, snippet)
    if end_position < len(text_list):
        snippet = u'{}{}'.format(snippet, ellipsis)
    
    return u'"{}"'.format(snippet)


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
                keyword_found = True
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

            if start > 0: # make sure hit wasn't at beginning of line
                start += 1
            if end < len(marked_text) -1: # same with end of line
                end -= 1

            # insert the highlighting tags
            # marked_text = marked_text[:start] + \
            #             '<font color="{}">'.format(color) + \
            #             marked_text[start:end] + \
            #             '</font>' + \
            #             marked_text[end:]
                        
            marked_text = '{}<font color="{}">{}</font>{}'.format(
                marked_text[:start],
                color,
                marked_text[start:end],
                marked_text[end:]
            )
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
    #print user_latlng, type(user_latlng[0]), type(user_latlng[1])
    sql_command = 'SELECT lat, lng FROM id_geocode WHERE id == ?'
    cursor = g.db.execute(sql_command, (id_,))
    locations_names = [description[0] for description in cursor.description]
    locations = cursor.fetchall()
    # [('lat', 'lng')]
    
    closest_distance = 25000
    for job_latlng in locations:
        #print job_latlng, type(job_latlng[0]), type(job_latlng[1])
        distance = vincenty.vincenty(user_latlng, job_latlng, miles=True)
        if distance < closest_distance:
            closest_distance = distance
    return closest_distance
        
    
    
    
    
    

    
    