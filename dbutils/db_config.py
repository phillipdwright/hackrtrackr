import os.path
import sqlite3
import json

from hackrtrackr import settings

# BASE_DB_FILE_PATH = os.path.join(settings.BASE_DIR, 'test_db')
BASE_DB_FILE_PATH = settings.BASE_DIR
db_name = settings.DATABASE_NAME
full_db_path = BASE_DB_FILE_PATH + db_name

#legacy, please don't delete - Greg
#posts_table = '''CREATE TABLE posts
#        (thread_date DATE, text TEXT, 
#        comment_date DATE, id INTEGER, thread_id INTEGER)'''
#posts_insert = "insert into posts values (?,?,?,?,?)"

#helper function to be used in the Table Class

def open_json(file):
    with open(file, 'r') as FH:
        data = json.load(FH)
    return data

#helper function to be used in the Table Class - convert tuple into column fields and data types
def tuple_list_to_string(tuple_list):
    string = ""
    for tup in tuple_list:
        for item in tup:
            string += item + " "
        string += ","
    final_string = string[:-1]
    return final_string

"""
# Column class is not currently in use  
class Column(object):
    def __init__(self, col_name, col_type):
        self.col_name = col_name
        self.col_type = col_type
    #if using tuple - 
    
    def __init__(self, tup):
        self.col_name = tup[0]       
        self.col_type = tup[1]
    """

class Table(object):
    def __init__(self, table_name, columns, data_source):
        self.table_name = table_name
        self.columns = columns 
        self.length = len(columns)
        self.data_source = data_source
    
    #Function that converts the columns tuple into query format
    # Example -> CREATE TABLE [table name] (thread_date DATE, text TEXT, 
    # comment_date DATE, id INTEGER, thread_id INTEGER)
    def create_table(self):
        base_query = "CREATE TABLE {}".format(self.table_name)
        query_addendum = "({})".format(tuple_list_to_string(self.columns))
        return base_query + query_addendum

    #query to insert a row into a table
    # example -> insert into posts values (?,?,?,?,?)"
    def insert_table(self, row):
        base_query = "INSERT INTO {} values ".format(self.table_name)
        vals = "?," * self.length
        new_vals = vals[:-1]
        query_text = base_query + "({})".format(new_vals)
        args = list((query_text, tuple(row)))
        return args
        # return "{} ({})".format(base_query, new_vals) ## Phil
    
def connect_db(db_name):
    return sqlite3.connect(db_name)

def db_exists():
    return os.path.isfile(full_db_path)

def create_db(starting_data, *tables):
    #load the historic json data
    #connect to DB, setup tables
    #data = open_json(starting_data)
    conn = connect_db(db_name)
    c = conn.cursor()
    
    #drop existing tables, create new ones and update them
    for t in tables:
        data = open_json(t.data_source)
        c.execute(('''DROP TABLE if exists {}''').format(t.table_name)) 
        c.execute(t.create_table())
        update_table(t, data, setup = True, conn = conn)

    #Validate DB creation
    z = conn.execute('''SELECT company from posts limit 10''')
    y = conn.execute('''SELECT website from company limit 10''')
    x = conn.execute('''SELECT lng from id_geocode limit 10''')
    print(z.fetchall())
    print(y.fetchall())
    print(x.fetchall())
    conn.close()

def update_table(table, data, setup = False, conn = None): #conn cannot be None if setup == True
    # if update_table is being used during first time DB setup, a connection to
    # DB will already be open
    if setup == False:
        conn = connect_db(db_name)
    print 'Entering update_table:'    
    c = conn.cursor()
    col_list = []
    for col in table.columns:
        col_list.append(col[0])
    for item in data:
        value = tuple(item["{}".format(cl)] for cl in col_list)
        query = table.insert_table(value)
        c.execute(query[0], query[1])
        
    conn.commit()
    
    if setup == False:
        conn.close()


"""
param = {"cols": [col1, col2, col3],
    "filters": {col1: value1, col2: value2}


"""


"""
latest v of create_db
def create_db(starting_data, *tables):
    #load the historic json data
    #connect to DB, setup tables
    data = open_json(starting_data)
    conn = connect_db(db_name)
    c = conn.cursor()
    
    #drop existing tables, create new ones and update them
    for t in tables:
        c.execute(('''DROP TABLE if exists {}''').format(t.table_name)) 
        c.execute(t.create_table())
        update_table(t, data, setup = True, conn = conn)
        
        col_list = []
        for col in t.columns:
            col_list.append(col[0])
        for item in data:
            value = tuple(item["{}".format(c)] for c in col_list)
            query = t.insert_table(value)
            c.execute(query[0], query[1])
            #c.execut(query_string, row_tuple) ## Phil
    
        conn.commit()
        
def tuple_list_to_string(tuple_list):
    string = ""
    for tup in tuple_list:
        for item in tup:
            string += item + " "
        string += ","
    final_string = string[:-1]
    return final_string
        
class Column(object):
    def __init__(self, col_name, col_type):
        self.col_name = col_name
        self.col_type = col_type
    #if using tuple - 
    
    def __init__(self, tup):
        self.col_name = tup[0]       
        self.col_type = tup[1]
    

class Table(object):
    def __init__(self, table_name, columns):
        self.table_name = table_name
        self.columns = columns 
        self.length = len(columns)
    
    def create_table(self):
        base_query = "CREATE TABLE {}".format(self.table_name)
        query_addendum = "({})".format(tuple_list_to_string(self.columns))
        return base_query + query_addendum

    def insert_table(self, row):
        base_query = "INSERT INTO {} values".format(self.table_name)
        vals = "?," * self.length
        new_vals = vals[:-1]
        return "{} ({}), ({})".format(base_query, new_vals, row)

def connect_db(db_name):
    return sqlite3.connect(db_name)

def db_exists():
    return os.path.isfile(full_db_path)

def create_db(starting_data, tables):
    #load the historic json data
    #comments_data = open_json(historic_data)
    #connect to DB, setup tables
    conn = connect_db(db_name)
    print("connection was made")
    
    c = conn.cursor()
    print("cursor was made")
    
    #drop existing tables, create new ones
    print("before for")
    
    for t in tables:
        print("into the t in tables for statement")
        c.execute(('''DROP TABLE if exists {}''').format(t.table_name)) 
        print("tables were dropped, now will try to create table")
        
        c.execute(t.create_table())
        
        print("table was created")
        
        col_list = []
        for col in t.columns:
            print(col)
            col_list.append(col[0])
        for item in starting_data:
            print("item")
            value = tuple(item["{}".format(c)] for c in col_list)
            c.execute(t.insert_table(value))
    
        conn.commit()
    
    #Validate DB creation
    x = conn.execute('''SELECT id from posts limit 10''')
    print(x.fetchall())
    conn.close()




old create_db() DON"T DELTE PLEASE!!!

#posts_table = '''CREATE TABLE posts
#        (thread_date DATE, text TEXT, 
#        comment_date DATE, id INTEGER, thread_id INTEGER)'''
#posts_insert = "insert into posts values (?,?,?,?,?)"

def create_db():
    #load the historic json data
    comments_data = open_json(historic_data)
    #connect to DB, setup tables
    conn = connect_db(db_name)
    c = conn.cursor()
    c.execute('''DROP TABLE if exists posts''') #need to put query in varible to avoid SQL injection?
    c.execute(posts_table)
    query = posts_insert
    columns = ['thread_date', 'text', 'comment_date', 'id', 'thread_id']
    #load json data into the db
    for item in comments_data:
        value = tuple(item["{}".format(c)] for c in columns)
        c.execute(query, value)
    conn.commit()
    
    #Validate DB creation
    x = conn.execute('''SELECT id from posts limit 10''')
    print(x.fetchall())
    conn.close()

"""

"""
Greg will delete this...at some point
class Column(object):
    def __init__(self, col_name, col_type):
        self.col_name = col_name
        self.col_type = col_type

def create_columns(dictionary):
    column_list = []
    for key, value in dictionary.iteritems():
        column_list.append(Column(key, value))
    return column_list
        
def create_table(table_name, columns_list):
"""