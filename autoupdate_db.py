import sqlite3

'''
Functions for automating database updates
'''

db = sqlite3.connect('test_db/testDB12.db')

sql_command = 'SELECT MAX(id) FROM posts'
cursor = db.execute(sql_command)
max_id = cursor.fetchone()[0]

print max_id

