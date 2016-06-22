from keyword_matching import datetime, read_in_json_file, re, DATE_INDEX, DATE_LIST, np, number_comments_per_month
from bs4 import BeautifulSoup
def get_urls(comments):
    '''
    Given all comments checks each for a regex match to url taken from SO
    http://stackoverflow.com/questions/6038061/regular-expression-to-find-urls-within-a-string
    '''
    p = re.compile('(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?', re.IGNORECASE)
    #p = re.compile('(http|ftp|https)://',re.IGNORECASE)

    for comment in comments:
        #soup = BeautifulSoup(comment['text'], "html.parser")
        
        #lines = soup.findAll(text=True)
        # this works but it splits everything by tags so you lose line info
        
        # so I use regex to go by the p tags
        p = re.compile(r'(<p>.*?</p>)')
        for m in p.finditer(comment['text']):
            line = m.group(1)
            soup = BeautifulSoup(line, "html.parser")
            line = ' '.join(soup.findAll(text=True))
            print line
        
        
        
       # if comment['created'] == datetime.date(2016,6,1):
       #     text = comment['text']
       #     text = text.replace('&#x2F;','/')
       #
       #     #if p.search(text):
       #     #    url = p.search(text).group(2)
       #     urls = []
       #     for m in p.finditer(text):
       #         urls.append(m.group(2))
       #     print ' '.join(urls)

    

            