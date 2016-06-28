import json
import copy
import datetime
import numpy as np
import calendar
import re
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta

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

# Filename for HN logo, used as default
HN_LOGO = 'hn_logo'

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
        #date += datetime.timedelta(days=32)
        #date = date.replace(day=1)
    return date_list
    
DATE_LIST = get_date_list(datetime.date(2011,4,1))
# create a dict so we can quickly get the index for each date
DATE_INDEX = {date:index for index, date in enumerate(DATE_LIST)}
DATE_LIST_STR = [date.isoformat() for date in DATE_LIST]

def keyword_check_comments_np_array(comments, keyword, prefix_suffix_flag=True, case_flag=False):
    '''
    Given comments as json
    Checks each comment for a keyword match
    if case_flag is True you require exact case match
    return a numpy array of counts in order of dates
    '''
    counts = np.zeros(len(DATE_LIST))
    keyword = re.escape(keyword) # escape special regex characters
    if prefix_suffix_flag:
        keyword = '(\W|^){}(\W|$)'.format(keyword) # so it can't be part of a larger word
    
    if case_flag:
        p = re.compile(keyword)
    else:
        p = re.compile(keyword, re.IGNORECASE)
        
    
    for comment in comments:
        if p.search(comment['text']):
            index = DATE_INDEX[comment['thread_date']]
            counts[index] += 1
    return counts
    
def number_comments_per_month(comments):
    '''
    Returns np array of total # of comments per month
    '''
    counts = np.zeros(len(DATE_LIST))
    
    for comment in comments:
        index = DATE_INDEX[comment['thread_date']]
        counts[index] += 1
    return counts

def get_matching_comments(comments, keywords):
    '''
    Return a list of matching comments from the last two months' posts
    '''
    # Find the first day of last month
    last_month = datetime.date.today().replace(day=1) + relativedelta(months=-1)
    
    # Build a list of all comments posted since the first of last month
    recent_comments = []
    for comment in comments:
        comment_date = comment['comment_date']
        if comment_date >= last_month:
            recent_comments.append(comment)
    
    # Build a list of recent comments that match the keywords
    matching_comments = []
    
    for comment in recent_comments:
        
        # Get the comment text
        text = BeautifulSoup(comment['text'], 'html.parser').get_text()
        
        # Verify that all keywords are found in the comment
        if all(keyword.lower() in text.lower() for keyword in keywords):
        
            # Get a comment snippet to use on the display page
            comment['snippet'] = _get_snippet(text, keywords)
            
            # Get rating and logo data from Glassdoor data
            try:
                company = find_company(text) # define
            except:
                company = None
            if company is not None:
                comment['rating'] = _get_rating(company) # define
                comment['logo'] = _get_logo(company) # define
            else:
                # Use the generic HN logo if there is no company match
                comment['logo'] = HN_LOGO
            
            # Append the comment to the matching comments list
            matching_comments.append(comment)
    
    # Sort the matching comments starting with most recent and return the list
    matching_comments = sorted(
        matching_comments,
        key=lambda comment: comment['comment_date'],
        reverse=True
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

# def find_company(text):
    
#     # Return the Glassdoor company id for Hulu
#     return 43242