import unittest
from update_db_helpers import compare_urls
from helpers import string_to_date, _keyword_check, _get_pure_text, get_keyword_regex
import settings
import sqlite3
import datetime
import re
from hn_search_api_helpers import get_thread_data_by_user, get_comments_from_thread, \
        json_date_to_string

DATABASE_FILE = settings.DATABASE_NAME

class UpdateDBTest(unittest.TestCase):
    
    def setUp(self):
        self.db = sqlite3.connect(DATABASE_FILE)
    
    def tearDown(self):
        self.db.close()
    
    def test_compare_urls(self):
        url1 = 'http://www.google.com'
        url2 = 'www.google.com'
        url3 = 'http://www.google.com/images'
        url4 = 'http://about.google.com'
        url5 = 'http://www.google.net'
        response = compare_urls(url1, url2)
        self.assertEqual(response, True)
        response = compare_urls(url1, url3)
        self.assertEqual(response, False)
        response = compare_urls(url1, url4)
        self.assertEqual(response, True)
        response = compare_urls(url1, url5)
        self.assertEqual(response, False)
        response = compare_urls(url4, url5)
        self.assertEqual(response, False)
        
class HelpersTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(DATABASE_FILE)
        sql_command = 'SELECT * FROM posts WHERE id == ?'
        cursor = self.db.execute(sql_command, (11816913,))
        posts_names = [description[0] for description in cursor.description]
        comment_list = cursor.fetchone()
        self.comment = {name:value for name,value in zip(posts_names,comment_list)}
        self.comment['pure_text'] = _get_pure_text(self.comment['text'])
        self.date = datetime.date(2016,1,1)
        
    def tearDown(self):
        self.db.close()
        
    def test_string_to_date(self):
        s = '2016-01-01'
        result = string_to_date(s)
        self.assertEqual(result, self.date)
        
    def test_keyword_check(self):
        p = re.compile('Academy')
        marked_text, total_keywords_found = _keyword_check(self.comment, [p])
        self.assertEqual(total_keywords_found, 1)
        
    def test_get_keyword_regex(self):
        '''
        The keyword must have a non-alphanumeric on both sides of it
        '''
        keyword = 'Banana'
        text1 = 'This sentence has a banana in it'
        text2 = 'This sentence has no bananas'
        text3 = 'banana bananas banana --banana--'
        regex = get_keyword_regex(keyword)
        
        hits = len(regex.findall(text1))
        self.assertEqual(hits,1)
        
        hits = len(regex.findall(text2))
        self.assertEqual(hits,0)

        hits = len(regex.findall(text3))
        self.assertEqual(hits,3)
        
    def test_get_keyword_regex_variant(self):
        '''
        certain keywords should be recognized as having variants
        '''
        keyword = 'nyc'
        text1 = 'a variant of new york city'
        regex = get_keyword_regex(keyword)
        hits = len(regex.findall(text1))
        self.assertEqual(hits, 1)
        
    def test_get_pure_text(self):
        '''
        Make sure html tags are removed
        '''
        html_text = '<p>We&#x27;re bringing a free, world-class education to anyone, anywhere.<p>'
        pure_text = u"We're bringing a free, world-class education to anyone, anywhere."
        result = _get_pure_text(html_text).strip()
        self.assertEqual(result, pure_text)
        
class HNApiTest(unittest.TestCase):
    def setUp(self): 
        self.date = datetime.date(2016,1,1)
        self.threads = get_thread_data_by_user('whoishiring')
        for thread in self.threads:
            if thread['created'] == datetime.date(2016,1,1):
                self.jan_thread = thread
                break
            
    def tearDown(self):
        pass
    
    def test_json_date_to_string(self):
        json_data = [{'date':datetime.date(2016,1,1)},{'date':datetime.date(2016,2,1)}]
        result_json = json_date_to_string(json_data)
        self.assertEqual(type(result_json[0]['date']), str)
    
    def test_get_comments_from_thread(self):
        comments = get_comments_from_thread(self.jan_thread)
        self.assertEqual(len(comments), 376)
        

if __name__ == '__main__':
    unittest.main()
    
    