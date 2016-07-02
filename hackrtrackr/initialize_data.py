from hn_search_api_helpers import main_write_threads, main_write_comments

'''
Usage: python initialize_data.py

This will first get the IDs of all HN 'Who is hiring?' threads using the HN
Search API, creating the file "data/threads.json"
Then it will get the comments from each threads
The comments will be stored as a single file with these fields:
    created: date of the job thread, for example "2011-1-1"
    parent_id: id of the job thread page
    id: id of comment itself, can be used to access url of comment
    text: comment text html format
This file will be "data/comments.json"
'''

# it would be nice to have a logger make a log of when the database was created
# and log all the updates as well...

main_write_threads()
# set the split_by_month_flag to True if you want separate files for each month
main_write_comments(split_by_month_flag = False)
