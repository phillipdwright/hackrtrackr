import sqlite3

def get_tables(db):
    '''Get the names of all tables contained in the db'''
    tab_query = "SELECT name FROM sqlite_master WHERE type = 'table';"
    tables = db.execute(tab_query).fetchall()
    table_names = [table[0] for table in tables]
    return table_names


def get_schemas(db, tables):
    '''Get the schema for each table in the db'''
    schemas = []
    schema_query = "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?;"
    
    for table in tables:
        schema = db.execute(schema_query, (table,)).fetchone()
        schemas.append({'table': table, 'schema': schema[0]})
    
    return schemas

def write_schema(db_file, db_conn):
    '''
    Write a file in the same directory as db_file with a sql schema script that 
    will create the db for the project.
    '''
    schema_file = db_file.replace('.db', '_schema.sql')
    
    with open(schema_file, 'w') as fn:
        fn.write('-- sqlite3 hackrtrackr.db < {}\n\n'.format(schema_file))
        fn.write('PRAGMA foreign_keys = ON;\n\n')
        
        tables = get_tables(db_conn)
        schemas = get_schemas(db_conn, tables)
        
        for schema in schemas:
            fn.write('--DROP TABLE if exists {};\n'.format(schema['table']))
            schema_string = schema['schema'].replace('(', '(\n  ')
            schema_string = schema_string.replace(' ,', ',\n  ')
            schema_string = schema_string.replace(' )', '\n)')
            fn.write('{};\n\n'.format(schema_string))

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        sys.exit('Usage: python inspect_db.py <db_filename>')
    
    # Connect to the database
    db_file = sys.argv[1]
    db = sqlite3.connect(db_file)

    tables = get_tables(db)
    print 'Tables:\n'
    print (table for table in tables)

    schemas = get_schemas(db, tables)
    for schema in schemas:
        print 'Schema for table {}:'.format(schema['table'])
        print schema['schema'], '\n'
    
    write_schema(db_file, db)