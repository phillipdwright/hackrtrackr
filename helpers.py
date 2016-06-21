import json
import copy
import datetime
import numpy as np
import calendar
import re

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
# create a dict so we can quickyl get the index for each date
DATE_INDEX = {date:index for index, date in enumerate(DATE_LIST)}
DATE_LIST_STR = [date.isoformat() for date in DATE_LIST]

def read_in_json_file(filename):
    '''
    Reads in json file
    Converts any 'created' fields from str to datetime
    '''
    with open(filename, 'r') as FH:
        json_data = json.load(FH)
    json_data = json_string_to_date(json_data)
    return json_data
    
def json_string_to_date(l):
    '''
    Given list of dicts
    Converts 'created' field from string to datetime.date
    Use if reading in json and want it as datetimes
    '''
    l_with_dates = copy.deepcopy(l)
    for i in l_with_dates:
        i['created'] = datetime.datetime.strptime(i['created'], '%Y-%m-%d').date()
    return l_with_dates
    
def keyword_check_comments_np_array(comments, keyword, suffix_flag=False, case_flag=False):
    '''
    Given comments as json
    Checks each comment for a keyword match
    if case_flag is True you require exact case match
    return a numpy array of counts in order of dates
    '''
    counts = np.zeros(len(DATE_LIST))
    
    if suffix_flag:
        keyword += '\W' # so it can't be part of a larger word
    
    if case_flag:
        p = re.compile(keyword)
    else:
        p = re.compile(keyword, re.IGNORECASE)
        
    
    for comment in comments:
        if p.search(comment['text']):
            index = DATE_INDEX[comment['created']]
            counts[index] += 1
    return counts