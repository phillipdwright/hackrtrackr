import re
import json
from bs4 import BeautifulSoup
import datetime
import numpy as np
import calendar
from helpers import number_comments_per_month, DATE_LIST_STR, DATE_INDEX
from hn_search_api_helpers import load_json_file, COMMENTS_FILE

KEYWORD_DICT_OLD = {
    'python':re.compile('(^|\W)(Python)($|\W)', re.IGNORECASE),
    'javascript':re.compile('(^|\W)(javascript|js)($|\W)', re.IGNORECASE),
    'SQL':re.compile('(^|\W)(SQL|Sequel)($|\W)', re.IGNORECASE),
    'Ruby':re.compile('(^|\W)(Ruby)($|\W)', re.IGNORECASE),
    'Java':re.compile('(^|\W)(Java)($|\W)', re.IGNORECASE),
    'PHP':re.compile('(^|\W)(PHP)($|\W)', re.IGNORECASE),
    'C++':re.compile('(^|\W)(C\+\+)($|\W)', re.IGNORECASE),
    'C':re.compile('(^|\W)(C)($|\W)'),
    'Go':re.compile('(^|\W)(Go)($|\W)'),
    'Scala':re.compile('(^|\W)(Scala)($|\W)', re.IGNORECASE),
    'React':re.compile('(^|\W)(React)($|\W)', re.IGNORECASE),
    'Objective-C':re.compile('(^|\W)(Objective-C|Objective C)($|\W)', re.IGNORECASE),
    'C#':re.compile('(^|\W)(C#)($|\W)', re.IGNORECASE),
    'Perl':re.compile('(^|\W)(Perl)($|\W)', re.IGNORECASE),
    'Erlang':re.compile('(^|\W)(Erlang)($|\W)', re.IGNORECASE),
    'R':re.compile('(^|\W)(R)($|\W)'),
    'Swift':re.compile('(^|\W)(Swift)($|\W)', re.IGNORECASE),
    'Haskell':re.compile('(^|\W)(Haskell)($|\W)', re.IGNORECASE),
    'Elixir':re.compile('(^|\W)(Elixir)($|\W)', re.IGNORECASE),
    'Rust':re.compile('(^|\W)(Rust)($|\W)', re.IGNORECASE),
    'HTML':re.compile('(^|\W)(HTML|HTML5)($|\W)'),
    'CSS':re.compile('(^|\W)(CSS)($|\W)'),
    'Bootstrap':re.compile('(^|\W)(Bootstrap)($|\W)', re.IGNORECASE),
    'iOS':re.compile('(^|\W)(iOS)($|\W)'),
    'Android':re.compile('(^|\W)(Android)($|\W)', re.IGNORECASE),
    'Windows':re.compile('(^|\W)(Windows)($|\W)', re.IGNORECASE),
    'Linux':re.compile('(^|\W)(Linux)($|\W)', re.IGNORECASE),
    'Unix':re.compile('(^|\W)(Unix)($|\W)', re.IGNORECASE),
    'Flask':re.compile('(^|\W)(Flask)($|\W)', re.IGNORECASE),
    'Django':re.compile('(^|\W)(Django)($|\W)', re.IGNORECASE),
    'AWS':re.compile('(^|\W)(AWS)($|\W)'),
    'Azure':re.compile('(^|\W)(Azure)($|\W)', re.IGNORECASE),
    'jQuery':re.compile('(^|\W)(jQuery)($|\W)', re.IGNORECASE),
    'Node':re.compile('(^|\W)(Node)($|\W)', re.IGNORECASE),
    'Redis':re.compile('(^|\W)(Redis)($|\W)', re.IGNORECASE),
    'Celery':re.compile('(^|\W)(Celery)($|\W)', re.IGNORECASE),
    'Mongo':re.compile('(^|\W)(Mongo)($|\W)', re.IGNORECASE),
    'Postgres':re.compile('(^|\W)(Postgres)($|\W)', re.IGNORECASE),
    'MySQL':re.compile('(^|\W)(MySQL)($|\W)', re.IGNORECASE),
    'Github':re.compile('(^|\W)(Github)($|\W)', re.IGNORECASE),
    'Git':re.compile('(^|\W)(Git)($|\W)', re.IGNORECASE),
    'Frontend':re.compile('(^|\W)(Frontend|Front-end|Front end)($|\W)', re.IGNORECASE),
    'Backend':re.compile('(^|\W)(Backend|Back-end|Back end)($|\W)', re.IGNORECASE),
    'Ansible':re.compile('(^|\W)(Ansible)($|\W)', re.IGNORECASE),
    'Remote':re.compile('(\W|^)(?<!no )(remote)(\W|$)', re.IGNORECASE), # ?<! is neg lookbehind
    'Onsite':re.compile('(^|\W)(Onsite|On-site|On site)($|\W)', re.IGNORECASE),
    'Internship':re.compile('(^|\W)(Intern|Interns|Internship|Internships)($|\W)', re.IGNORECASE),
    'Full-time':re.compile('(^|\W)(Full time|Full-time|Fulltime)($|\W)', re.IGNORECASE),
    'Visa':re.compile('(\W|^)(?<!no )(Visa|Visas)(\W|$)', re.IGNORECASE),
    'H1B':re.compile('(\W|^)(H1B|H1Bs)(\W|$)', re.IGNORECASE),
    'Rails':re.compile('(\W|^)(Rails)(\W|$)', re.IGNORECASE),
    'DevOps':re.compile('(\W|^)(DevOps|Dev-ops|Dev ops)(\W|$)', re.IGNORECASE)
    
    }

# make them all lowercase so it is easy to access the db fields
KEYWORD_DICT = {}
for keyword in KEYWORD_DICT_OLD:
    KEYWORD_DICT[keyword.lower()] = KEYWORD_DICT_OLD[keyword]

def check_all_keywords(comments):
    '''
    runs through each comment and does a regex search for each keyword
    adds a bool field for if the comment has or doesn't have a hit
    this new json file is written out
    '''
    #n = 0
    for comment in comments:
        text = BeautifulSoup(comment['text'], 'html.parser').get_text()
        for key,p in KEYWORD_DICT.items():
            if p.search(text):
                comment[key] = True
            else:
                comment[key] = False
        
        #n += 1
        #if not n%1000:
        #    print 'n'
    with open('data/comments_glassdoor_keywords.json','w') as FHOUT:
        json.dump(comments, FHOUT)
            
def keyword_count_table():
    '''
    given a json file that has bool for keywords
    it makes an entry for each keyword and gets a list of the counts
    normalized by total counts
    and outputs this as a json file
    the idea is this could be quickly read in for making the trend plots
    '''
    comments = load_json_file('data/comments_glassdoor_keywords.json')
    
    total_counts = np.zeros(len(DATE_LIST_STR))
    keyword_counts = {}
    for key in KEYWORD_DICT:
        keyword_counts[key]  = np.zeros(len(DATE_LIST_STR))

    for comment in comments:
        index = DATE_INDEX[comment['thread_date']]
        total_counts[index] += 1
        
        for keyword in KEYWORD_DICT:
            if comment[keyword]:
                keyword_counts[keyword][index] += 1
    output_json = []

    for keyword in keyword_counts:
        keyword_counts_normalized = keyword_counts[keyword] / total_counts

        # convert from numpy array to list since numpy can't go to json
        counts_list = list(keyword_counts_normalized)

        d = dict(keyword=keyword.lower(), counts=counts_list)
        output_json.append(d)

    # add the total counts to the output_json
    d = dict(keyword="Total Counts", counts=list(total_counts))
    output_json.append(d)
    
    with open('data/keyword_counts_table.json','w') as FHOUT:
        json.dump(output_json, FHOUT)

def keyword_count(regex_pattern, comments):
    count = 0
    for comment in comments:
        #text = BeautifulSoup(comment['text'], 'html.parser').get_text()
        if regex_pattern.search(comment['text']):
            count += 1
            
    return count
    
  
with open('data/comments_glassdoor.json','r') as FH:
    comments = json.load(FH)    
check_all_keywords(comments)
# p = re.compile('(^|\W)MySQL($|\W)', re.IGNORECASE)    
# print keyword_count(KEYWORD_DICT['javascript'], comments)
keyword_count_table()      