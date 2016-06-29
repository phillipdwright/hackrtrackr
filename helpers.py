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
from bokeh.plotting import figure
from bokeh.models import NumeralTickFormatter
import os.path

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
HN_LOGO = 'img/logos/hn_logo.png'

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
    end_date = datetime.date(2016,6,1) # don't want july showing up in plot
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

def plot_dots_and_line(fig, counts, keyword, color):   
    '''
    given: fig for bokeh plot, counts np array, keyword, color
    adds a dot and line plot of counts
    returns: fig
    '''
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
    return fig
    
def make_fig(keywords):
    '''
    given: list of keywords
    generates a bokeh fig with a dot and line graph of each keyword
    also deals with special case of no keywords to get total posts
    returns: fig
    '''
    cached_counts_json = load_json_file(CACHED_COUNTS_FILE) # has both keyword counts and total counts
    cached_counts = {}
    for entry in cached_counts_json:
        cached_counts[entry['keyword']] = entry['counts']
    
    fig = figure(
            x_axis_type = "datetime",
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
    
    # if no keywords get total posts per month
    if not keywords:
        fig.yaxis[0].formatter = NumeralTickFormatter(format="0,0")
        counts = np.array(cached_counts['Total Counts'])
        fig = plot_dots_and_line(fig, counts, 'All', COLORS[0])
        
    for keyword, color in zip(keywords, COLORS):
        # would it be faster to check all keywords for each comment
        # instead of doing one keyword at a time through all comments?
        # if we are doing html-> text for each comment I think so...
        cached_keywords = cached_counts.keys()
        cached_keywords = [i.lower() for i in cached_keywords]
        
        if keyword.lower() in cached_keywords:
            #print 'got cached counts for {}'.format(keyword)
            counts = np.array(cached_counts[keyword.lower()])
        else:
            counts = keyword_check(keyword)
            counts /= np.array(cached_counts['Total Counts'])
        fig = plot_dots_and_line(fig, counts, keyword, color)
        
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
    
def keyword_check(keyword, prefix_suffix_flag=True, case_flag=False):
    '''
    
    '''
    sql_command = 'SELECT thread_date, text FROM posts'
    cursor = g.db.execute(sql_command)
    comments = cursor.fetchall()
    
    counts = np.zeros(len(DATE_LIST))
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
        if p.search(text):
            index = DATE_INDEX[string_to_date(date)]
            counts[index] += 1
    return counts

# def get_matching_comments_old(comments, keywords):
#     '''
#     Return a list of comments from the current and previous month's threads
#     that match all the keywords
#     '''
#     # Find the first day of last month
#     last_month = datetime.date.today().replace(day=1) + relativedelta(months=-1)
    
#     # Build a list of all comments posted since the first of last month
#     recent_comments = []
#     for comment in comments:
#         comment_date = comment['comment_date']
#         if comment_date >= last_month:
#             recent_comments.append(comment)
    
#     # Build a list of recent comments that match the keywords
#     matching_comments = []
    
#     for comment in recent_comments:
        
#         # Get the comment text
#         text = BeautifulSoup(comment['text'], 'html.parser').get_text()
#         #text = comment['text']
#         # Verify that all keywords are found in the comment
#         if all(keyword.lower() in text.lower() for keyword in keywords):
        
#             # Get a comment snippet to use on the display page
#             comment['snippet'] = _get_snippet(text, keywords)
            
#             # Get rating and logo data from Glassdoor data
#             try:
#                 company = find_company(text) # define
#             except:
#                 company = None
#             if company is not None:
#                 comment['rating'] = _get_rating(company) # define
#                 comment['logo'] = _get_logo(company) # define
#             else:
#                 # Use the generic HN logo if there is no company match
#                 comment['logo'] = HN_LOGO
            
#             # Append the comment to the matching comments list
#             matching_comments.append(comment)
    
#     location_match = False
#     # TODO:
#     # location_match = get_distances(recent_comments, location)
#     # Test to see if we can match location.  If so, define comment['distance']
#     # and set location_match = True.
    
#     if location_match:
#         key = lambda comment: comment['distance']
#         reverse = False
#     else:
#         key = lambda comment: comment['comment_date']
#         reverse = True
    
#     # Sort the matching comments starting with most recent and return the list
#     matching_comments = sorted(
#         matching_comments,
#         key=key,
#         reverse=reverse
#     )
    
#     return matching_comments
 
def get_matching_comments(keywords):
    # Build a list of all comments posted from June 2016
    sql_command = 'SELECT * FROM posts WHERE \
                thread_date BETWEEN "2016-05-05" AND "2016-07-07"'
    cursor = g.db.execute(sql_command)
    names = [description[0] for description in cursor.description]
    recent_comments = cursor.fetchall()
    
    # Build a list of recent comments that match the keywords
    matching_comments = []
    
    # compile pattersn for each keyword
    patterns = []
    for keyword in keywords:
        keyword = re.escape(keyword)
        keyword = '(\W|^){}(\W|$)'.format(keyword)
        p = re.compile(keyword, re.IGNORECASE)
        patterns.append(p)
    
    for comment_list in recent_comments:
        comment = {name:value for name,value in zip(names,comment_list)}
        if 'thread_date' not in comment:
            print comment
        comment['thread_date'] = string_to_date(comment['thread_date'])
        comment['comment_date'] = string_to_date(comment['comment_date'])
        total_keywords_found = 0
        marked_text = comment['text']
        text = BeautifulSoup(comment['text'], 'html.parser').get_text()
        
        for pattern, color in zip(patterns, HEX_COLORS):
            keyword_found = False
            start_ends = []
            for m in pattern.finditer(marked_text):
                keyword_found = True
                start_ends.append((m.start(), m.end()))
            if keyword_found:
                total_keywords_found += 1
            for start_end in start_ends[::-1]:
                start = start_end[0]
                end = start_end[1]
                if start > 0:
                    start += 1
                if end < len(marked_text) -1:
                    end -= 1

                marked_text = marked_text[:start] + \
                            '<font color="{}">'.format(color) + \
                            marked_text[start:end] + \
                            '</font>' + \
                            marked_text[end:]
        comment['marked_text'] = marked_text
        
        # Verify that all keywords are found in the comment 
        # (bug/feature - also works for 0 keywords)
        if total_keywords_found == len(keywords):
        
            # Get a comment snippet to use on the display page
            #comment['snippet'] = _get_snippet(text, keywords)
            comment['snippet'] = comment['company']
            # Get rating and logo data from Glassdoor data
            # sql_command = 'SELECT * FROM company WHERE id == {}'.format(comment['glassdoor_id'])
            # cursor = g.db.execute(sql_command)
            # names = [description[0] for description in cursor.description]
            # recent_comments = cursor.fetchall()
            
            try:
                company = comment['company'] # define
            except:
                company = None
            if company is not None: 
                comment['rating'] = _get_rating(company) # define
                comment['logo'] = _get_logo(company) # define
                if comment['glassdoor_id']:
                    filename = 'static/img/logos/{}.png'.format(comment['glassdoor_id'])
                    if os.path.isfile(filename):
                        comment['logo'] = 'img/logos/{}.png'.format(comment['glassdoor_id'])
                    else:
                        comment['logo'] = HN_LOGO
                else:
                    comment['logo'] = HN_LOGO
            else:
                # Use the generic HN logo if there is no company match
                comment['logo'] = HN_LOGO
            
            # Append the comment to the matching comments list
            matching_comments.append(comment)
    
    location_match = False
    # TODO:
    # location_match = get_distances(recent_comments, location)
    # Test to see if we can match location.  If so, define comment['distance']
    # and set location_match = True.
    
    if location_match:
        key = lambda comment: comment['distance']
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


#################################
#                               #
# HELPER FUNCTIONS YET TO WRITE #
#                               #
#################################

def find_company(text): # can use 'company' field in comments_db.json
    pass

def _get_rating(text):
    pass

def _get_logo(text): # May not need this one?  Think I just need company ID
    pass