import re
import json
import os
from bs4 import BeautifulSoup
import datetime
import collections
import geocoder
import sys
import time

from hackrtrackr import settings

GEO = os.path.join(settings.BASE_DIR, 'dbutils', 'data', 'geo')
US_CITIES_FILE = os.path.join(GEO, 'us_cities.txt') # Line 52
US_STATES_FILE = os.path.join(GEO, 'us_states.txt') # Line 62
COUNTRIES_FILE = os.path.join(GEO, 'countries.txt') # Line 72
CANADA_PROVINCES_FILE = os.path.join(GEO, 'canada_provinces.txt') # Line 82
CITY_TO_COUNTRY_FILE = os.path.join(GEO, 'city_to_country.json') # Line 21


with open(CITY_TO_COUNTRY_FILE, 'r') as FH:
# with open('../data/cities/city_to_country.json', 'r') as FH:
    json_data = json.load(FH)
    
city_to_country = json_data[0]
#print city_to_country['but in']



US_STATES = ['WA', 'WI', 'WV', 'FL', 'WY', 'NH', 'NJ', 'NM', 'NA', 'NC', 'ND', 
        'NE', 'NY', 'RI', 'NV', 'GU', 'CO', 'CA', 'GA', 'CT', 'OK', 'OH', 'KS', 
        'SC', 'KY', 'OR', 'SD', 'DE', 'DC', 'HI', 'PR', 'TX', 'LA', 'TN', 'PA', 
        'VA', 'VI', 'AK', 'AL', 'AS', 'AR', 'VT', 'IL', 'IN', 'IA', 'AZ', 'ID', 
        'ME', 'MD', 'MA', 'UT', 'MO', 'MN', 'MI', 'MT', 'MP', 'MS']
        
CAN_STATES = ['AB', 'BC', 'YT', 'ON', 'NL', 'MB', 'NB', 'SK', 'QC', 'PE', 'NS', 'NT', 'NU']

# key is geocoder city, value is any other way it could be written
city_dict = {'SF': ['SF', 'San Francisco', 'San Fran', 'Frisco', 'S.F.'], 
            'New York': ['NYC', 'New York City', 'NY', 'N.Y.','Brooklyn','Manhattan','York City','York Metro'], 
            'Los Angeles':['LA','Los Angeles'],
            'KCMO':['KC', 'Kansas City'],
            'Santa Clarita':['Valencia'],
            'Tysons':['Tysons Corner'],
            'Lynnwood': ['Lynwood'],
            'St. Louis': ['Louis']
}



us_city_states = []
#with open('../data/cities/us_cities.txt') as FH:
with open(US_CITIES_FILE) as FH:
    for line in FH:
        line = line.rstrip()
        l = line.split('\t')
        city, state = l[1], l[2]
        us_city_states.append((city, state))
        
us_states_full_name = []
us_abbrev_to_state = {}
#with open('../data/us_states.txt') as FH:
with open(US_STATES_FILE) as FH:
    for line in FH:
        line = line.rstrip()
        l = line.split('\t')
        abbrev, state = l[0].strip(), l[1].strip()
        us_abbrev_to_state[abbrev] = state
        us_states_full_name.append(state)
        
countries = []
#with open('../data/cities/countries.txt') as FH:
with open(COUNTRIES_FILE) as FH:
    for line in FH:
        line = line.rstrip()
        l = line.split('\t')
        country = l[1]
        country = country.split('(')[0]
        countries.append(country)
        
canada_abbrev_to_state = {}
#with open('../data/canada_provinces.txt') as FH:
with open(CANADA_PROVINCES_FILE) as FH:
    for line in FH:
        line = line.rstrip()
        l = line.split('\t')
        abbrev, state = l[1].strip(), l[0].strip()
        canada_abbrev_to_state[abbrev] = state
        
STATE_REGEX = '(' + us_states_full_name[0]
for state in us_states_full_name:
    STATE_REGEX += '|' + state
STATE_REGEX += ')'
#STATE_REGEX = '(([A-Z]{1}[A-z]+ )?[A-Z]{1}[A-z]+)(,|, | )' + STATE_REGEX + '(\W|$)'
STATE_REGEX = '((New )?([A-Z][A-z]+\.? )?[A-Z][A-z]+)(,|, | )(' + STATE_REGEX + ')(\W|$)'
STATE_RE = re.compile(STATE_REGEX)
STATE_ABBR_REGEX = '(([A-Z][^ A-Z\W]{2,} ?){1,2})(, |,| )([A-Z]{2})(\W|$)'
STATE_ABBR_REGEX = '((New )?([A-Z][A-z]+\.? )?[A-Z][A-z]+)(,|, | )([A-Z]{2})(\W|$)'
STATE_ABBR_RE = re.compile(STATE_ABBR_REGEX)

COUNTRY_REGEX = '(' + countries[0]
for country in countries:
    COUNTRY_REGEX += '|' + country
COUNTRY_REGEX += ')'
COUNTRY_REGEX = '(([A-Z]{1}[A-z]+ )?[A-Z]{1}[A-z]+)(,|, | )' + COUNTRY_REGEX + '(\W|$)'
COUNTRY_RE = re.compile(COUNTRY_REGEX, re.IGNORECASE)

COUNTRY_REGEX = '(' + countries[0]
for country in countries:
    COUNTRY_REGEX += '|' + country
COUNTRY_REGEX += ')'
COUNTRY_NAME_ONLY_REGEX = '(^|\W)(' + COUNTRY_REGEX + ')(\W|$)'
COUNTRY_NAME_ONLY_RE = re.compile(COUNTRY_NAME_ONLY_REGEX, re.IGNORECASE)

STATE_REGEX = '(' + us_states_full_name[0]
for state in us_states_full_name:
    STATE_REGEX += '|' + state
STATE_REGEX += ')'
STATE_NAME_ONLY_REGEX = '(^|\W)(' + STATE_REGEX + ')(\W|$)'
STATE_NAME_ONLY_RE = re.compile(STATE_NAME_ONLY_REGEX, re.IGNORECASE)

def load_json_file(filename):
    '''
    given: json file
    converts any isoformat date fields from str to datetime.date
    returns: list of dicts
    '''
    with open(filename, 'r') as FH:
        json_data = json.load(FH)
    return json_data
    
def check_country_only(line):
    '''
    only looks for country name
    '''
    found_locations = []
    found_positions = []
    
    for m in COUNTRY_NAME_ONLY_RE.finditer(line):
        city_match = False
        country = m.group(2).strip()
        
        found_positions.append((m.start(), m.end()))
        found_locations.append((None, None, country))

    for pos in found_positions:
        replace_length = pos[1] - pos[0]
        line = line[:pos[0]] + ' '*replace_length + line[pos[1]:]

    return line, found_locations 
    
def check_state_only(line):
    '''
    only looks for state name
    '''
    found_locations = []
    found_positions = []
    
    for m in STATE_NAME_ONLY_RE.finditer(line):
        city_match = False
        state = m.group(2).strip()
        
        found_positions.append((m.start(), m.end()))
        found_locations.append((None, state, 'US'))

    for pos in found_positions:
        replace_length = pos[1] - pos[0]
        line = line[:pos[0]] + ' '*replace_length + line[pos[1]:]

    return line, found_locations 
    
def check_countries_regex(line):
    '''
    looks for city, country with country spelled out
    '''
    found_locations = []
    found_positions = []
    
    for m in COUNTRY_RE.finditer(line):
        city_match = False
        city, country = m.group(1).strip(), m.group(4).strip()
        #print city
        #print country
        if city in city_to_country:
            #print 'gote here'
            #print city_to_country[city]
            if country.lower() in [i.lower() for i in city_to_country[city]]:
                city_match = True
        else:
            city_split = city.split()
            if len(city_split) == 2 and city_split[1] in city_to_country:
                city = city_split[1]
                city_match = True
            #print city, country

        if city_match:
            #print city
            found_positions.append((m.start(), m.end()))
            found_locations.append((city, None, country))

    for pos in found_positions:
        replace_length = pos[1] - pos[0]
        line = line[:pos[0]] + ' '*replace_length + line[pos[1]:]

    return line, found_locations 
    
def check_city_state(line):
    '''
    Looks for City State with State being spelled out
    but what about New York issues...
    '''
    found_locations = []
    found_positions = []
    for m in STATE_RE.finditer(line):
        city_match = False
        city, state = m.group(1).strip(), m.group(5).strip()
        if city in city_to_country and state in city_to_country[city]:
            city_match = True
        else:
            pass
            #print city, state
        if city_match:
            found_positions.append((m.start(), m.end()))
            #found_locations.append((city, None, country))
            found_locations.append((city, state, 'US'))
    for pos in found_positions:
        replace_length = pos[1] - pos[0]
        line = line[:pos[0]] + ' '*replace_length + line[pos[1]:]

    return line, found_locations     
    
def check_major_cities(line):
    major_cities = ['San Francisco', 'SF', 'S.F.', 'Los Angeles', 'L.A.', 'New York City', 'NYC', 'N.Y.C.']

def check_city_st(line):
    '''
    given: line of text
    search for possible locations
    a location is (city, state, country)
    there could be multiple locations per line so return a list
    '''
    # stole regex from here: https://github.com/gaganpreet/hn-hiring-mapped/blob/gh-pages/src/parse.py
    # it matches City, ST
    # I modified it to make the comma optional, but could check if this matters
    found_locations = []
    found_positions = []
    #for m in re.finditer(r'(([A-Z][^ A-Z\W]{2,} ?){1,2})(, |,| )([A-Z]{2})(\W|$)', line):
    for m in STATE_ABBR_RE.finditer(line):
        city, state = m.group(1).strip(), m.group(4).strip()
        country = None
        if state in US_STATES:
            country = 'USA'
        elif state in CAN_STATES:
            country = 'Canada'
        elif state == 'UK':
            country = state
            state = 'England'
        elif state == 'AU':
            country = state
            state = None
        elif state == 'US': # cases like New York, US etc
            country = state
            state = None
        else:
            #print('Could not identify {}, {}'.format(city, state))
            continue
        g_string = ' '.join(i for i in (city, state, country) if i)
        g = geocoder.google(g_string)
        tries = 0
        while not g.city and tries < 5:
            tries += 1
            time.sleep(tries)
            g_string = ' '.join(i for i in (city, state, country) if i)
            g = geocoder.google(g_string)
        city_match = True
        if city == g.city and state != g.state:
            print city, state, g.state
            print line
        if city != g.city:
            if g.city not in city_dict or city not in city_dict[g.city]:
                city_match = False
                #g_city = g.city
                #if g.city:
                #    g_city = g_city.encode('utf-8')
                #print('Cities dont match {}, {}, {}'.format(city, g_city, g_string))
                # q = raw_input()
                # if q == 'q':
                #     sys.exit()
        if city_match:
            #replace_length = m.end() - m.start()
            #new_line = line[:m.start()] + 'x'*replace_length + line[m.end:]
            #print('Cities match {}, {}'.format(city, g.city))
            found_positions.append((m.start(), m.end()))
            found_locations.append((g.city, g.state, g.country))
    if found_positions:
        pass
        #print line, found_locations
    for pos in found_positions:
        replace_length = pos[1] - pos[0]
        line = line[:pos[0]] + ' '*replace_length + line[pos[1]:]
    #print line
    
    # q = raw_input()
    # if q == 'q':
    #     sys.exit()
        
    #check_line_for_state_named_regex(line)
    return line, found_locations    

    
def check_city_st_2(line):
    '''
    given: line of text
    search for possible locations
    a location is (city, state, country)
    there could be multiple locations per line so return a list
    '''
    # stole regex from here: https://github.com/gaganpreet/hn-hiring-mapped/blob/gh-pages/src/parse.py
    # it matches City, ST
    # I modified it to make the comma optional, but could check if this matters
    found_locations = []
    found_positions = []
    #for m in re.finditer(r'((New )?([A-Z][A-z]+\.? )?[A-Z][A-z]+)(, |,| )([A-Z]{2})(\W|$)', line):
    for m in STATE_ABBR_RE.finditer(line):
        city, state = m.group(1).strip(), m.group(5).strip()
        country = None
        if state in US_STATES:
            country = 'USA'
        elif state in CAN_STATES:
            country = 'Canada'
        elif state == 'UK':
            country = state
            state = None
        elif state == 'AU':
            country = state
            state = None
        elif state == 'US': # cases like New York, US etc
            country = state
            state = None
        else:
            #print('Could not identify {}, {}'.format(city, state))
            continue
        
        if city not in city_to_country:
            city_split = city.split()
            if len(city_split) == 3 and city_split[0] == 'New' and city_split[1] == 'York':
                city = 'New York City'
            elif len(city_split) > 1:
                if city_split[1] in city_to_country:
                    city = city_split[1]
                else:
                    return line, []
            else:
                return line, []
        
        city_match = True
        if state in US_STATES:
            if city in city_to_country:
                if us_abbrev_to_state[state] in city_to_country[city]:
                    pass
                else:
                    city_match = False
            else:
                city_match = False
        if city_match:
            found_positions.append((m.start(), m.end()))
            found_locations.append((city, state, country))

    for pos in found_positions:
        replace_length = pos[1] - pos[0]
        line = line[:pos[0]] + ' '*replace_length + line[pos[1]:]

    return line, found_locations 
    
def check_city_name(line):
    found_locations = []
    found_positions = []
    cities_to_try = {
        'San Francisco':['San Francisco', 'SF', 'Bay Area','Silicon Valley'],
        'New York City':['New York City', 'New York', 'NYC', 'NY'],
        'London':['London'],
        'Boston':['Boston'],
        'Los Angeles':['Los Angeles','LA','L\.A\.','Southbay'],
        'Seattle':['Seattle'],
        'Berlin':['Berlin'],
        'Chicago':['Chicago'],
        'Palo Alto':['Palo Alto'],
        'Toronto':['Toronto'],
        'Amsterdam':['Amsterdam'],
        'San Mateo':['San Mateo'],
        'Mountain View':['Mountain View'],
        'Atlanta':['Atlanta'],
        'Paris':['Paris'],
        'Portland':['Portland'],
        'Denver':['Denver'],
        'Redwood City':['Redwood', 'Redwood City'],
        'Boulder':['Boulder'],
        'San Diego':['San Diego'],
        'Minneapolis':['Minneapolis'],
        'Phoenix':['Phoenix'],
        'Singapore':['Singapore'],
        'Sunnyvale':['Sunnyvale'],
        'Sydney':['Sydney'],
        'Vancouver':['Vancouver'],
        'Dublin':['Dublin'],
        'Montreal':['Montreal'],
        'Philadelphia':['Philadelphia'],
        'San Jose':['San Jose'],
        'Shanghai':['Shanghai'],
        'Bangalore':['Bangalore'],
        'Berkeley':['Berkeley'],
        'Dallas':['Dallas'],
        'Hong Kong':['Hong Kong'],
        'Irvine':['Irvine'],
        'Melbourne':['Melbourne'],
        'Munich':['Munich'],
        'Charlotte':['Charlotte'],
        'Miami':['Miami'],
        'Milan':['Milan'],
        'Ottawa':['Ottawa'],
        'Santa Barbara':['Santa Barbara'],
        'Edinburgh':['Edinburgh'],
        'Raleigh':['Raleigh'],
        'Delhi':['Delhi'],
        'Pune':['Pune'],
        'Malaga':['Malaga'],
        'Tel-Aviv':['Tel-Aviv'],
        'Warsaw':['Warsaw'],
        'Bengaluru':['Bengaluru'],
        'Barcelona':['Barcelona'],
        'Santa Monica':['Santa Monica'],
        #'Washington DC':['Washington D\.C\.'],
        'Luxembourg':['Luxembourg'],
        'Cupertino':['Cupertino'],
        'Oakland':['Oakland'],
        'Anaheim':['Anaheim'],
        'Copenhagen':['Copenhagen'],
        'Herzliya':['Herzliya'],
        'Gurgaon':['G-town'],
        'Bochum':['Bochum'],
        'Stuttgart':['Stuttgart'],
        'Ann Arbor':['Ann Arbor'],
        'Pasadena':['Pasadena'],
        'Austin':['Austin'],
        'The Hague':['The Hague'],
        'Buenos Aires':['Buenos Aires'],
        'New Orleans':['New Orleans']
    }
    for city in cities_to_try:
        for alias in cities_to_try[city]:
            p = re.compile('(^|\W)('+alias+')($|\W)',re.IGNORECASE)
            for m in p.finditer(line):
                country = city_to_country[city][0]
                found_positions.append((m.start(), m.end()))
                state = None
                if country in us_states_full_name:
                    state  =country
                    country = 'US'
                    
                found_locations.append((city, state, country))
                
    for pos in found_positions:
        replace_length = pos[1] - pos[0]
        line = line[:pos[0]] + ' '*replace_length + line[pos[1]:]

    return line, found_locations  
    
def check_line_for_location(line):
    '''
    returns list of locations found in single line
    '''
    locs = []
    line, found_locs = check_city_st_2(line)
    #print 'line after check_city_st_2', line
    if found_locs:
        locs += found_locs
    line, found_locs = check_countries_regex(line)
    if found_locs:
        locs += found_locs
    
    line, found_locs = check_city_state(line)
    if found_locs:
        locs += found_locs
        
    line, found_locs = check_city_name(line)
    if found_locs:
        locs += found_locs

    
    if not locs:
        line, found_locs = check_state_only(line)
        if found_locs:
            locs += found_locs
        line, found_locs = check_country_only(line)
        if found_locs:
            locs += found_locs
    return line, locs
    
def check_comment_for_location(comment):
    '''
    returns list of locations found in comment
    '''
    soup = BeautifulSoup(comment['text'], "html.parser")
    locs = []   
    
    for pos, i in enumerate(soup.findAll('p')):
        line = ' '.join(i.findAll(text=True))
        line, found_locs = check_city_st_2(line)
        if found_locs:
            locs += found_locs
        line, found_locs = check_countries_regex(line)
        if found_locs:
            locs += found_locs
            
        line, found_locs = check_city_state(line)
        if found_locs:
            locs += found_locs
            
        line, found_locs = check_city_name(line)
        if found_locs:
            locs += found_locs
        
        
        if not locs:
            line, found_locs = check_state_only(line)
            if found_locs:
                locs += found_locs
            line, found_locs = check_country_only(line)
            if found_locs:
                locs += found_locs
        
        if locs:
            break
        if 'remote' in line.lower():
            break # stop if it is a remote job
        
    loc_strings = []
    for loc in locs:
        t = (i for i in loc if i)
        s = ' '.join(t)
        if s not in loc_strings:
            loc_strings.append(s)
    return loc_strings
    
def check_locations(json_file):
    '''
    given: comments.json
    check text of each comment for a location
    returns: ?
    '''
    json_data = load_json_file(json_file)
    line_num_hit = collections.defaultdict(int)
    has_hit = 0
    total = 0
    output_json = []
    for comment in json_data:
        if comment['thread_date'] == '2016-07-01':
            soup = BeautifulSoup(comment['text'], "html.parser")
            locs = []   
            
            for pos, i in enumerate(soup.findAll('p')):
                line = ' '.join(i.findAll(text=True))
                line, found_locs = check_city_st_2(line)
                if found_locs:
                    #print 'a'
                    locs += found_locs
                    
                line, found_locs = check_countries_regex(line)
                if found_locs:
                    #print 'b'
                    locs += found_locs
                    
                line, found_locs = check_city_state(line)
                if found_locs:
                    #print 'd'
                    locs += found_locs
                    
                line, found_locs = check_city_name(line)
                if found_locs:
                    #print 'c'
                    locs += found_locs

                
                if not locs:
                    line, found_locs = check_state_only(line)
                    if found_locs:
                        locs += found_locs
                    line, found_locs = check_country_only(line)
                    if found_locs:
                        locs += found_locs
                
                if locs:
                    has_hit += 1
                    line_num_hit[pos] += 1
                    break
                if 'remote' in line.lower():
                    break # stop if it is a remote job

            # text_lines = []
            # for pos, i in enumerate(soup.findAll('p')):
            #     line = ' '.join(i.findAll(text=True))
            #     text_lines.append(line)
                
            # for pos, line in enumerate(text_lines):
            #     line, found_locs = check_city_st_2(line)
            #     if found_locs:
            #         print line
            #         text_lines[pos] = line
            #         line_num_hit[pos] += 1
            #         locs += found_locs
            #         break

            # for pos, line in enumerate(text_lines):
            #     line, found_locs = check_countries_regex(line)
            #     if found_locs:
            #         print line
            #         text_lines[pos] = line
            #         line_num_hit[pos] += 1
            #         locs += found_locs
            #         break
                
            # for pos, line in enumerate(text_lines):
            #     line, found_locs = check_city_name(line)
            #     if found_locs:
            #         print line
            #         text_lines[pos] = line
            #         line_num_hit[pos] += 1
            #         locs += found_locs
            #         break
                
            # for pos, line in enumerate(text_lines):
            #     line, found_locs = check_city_state(line)
            #     if found_locs:
            #         print line
            #         text_lines[pos] = line
            #         line_num_hit[pos] += 1
            #         locs += found_locs
            #         break
                
            # if not locs: # only last resort if no location found
            #     for pos, line in enumerate(text_lines):
            #         line, found_locs = check_state_only(line)
            #         if found_locs:
            #             text_lines[pos] = line
            #             line_num_hit[pos] += 1
            #             locs += found_locs
            #             break
            # if not locs: # last resort if no location found
            #     for pos, line in enumerate(text_lines):
            #         line, found_locs = check_country_only(line)
            #         if found_locs:
            #             text_lines[pos] = line
            #             line_num_hit[pos] += 1
            #             locs += found_locs
            #             break
                
            # if locs and pos > 0:
            #     for pos, i in enumerate(soup.findAll('p')):
            #         line = ' '.join(i.findAll(text=True))
            #         print line
            #     print '\n'
            #     print locs
            #     print '\n'
            #     q = raw_input()
            #     if q == 'q':
            #         sys.exit()
           
            total += 1
            #print locs
            loc_strings = []
            for loc in locs:
                t = (i for i in loc if i)
                s = ' '.join(t)
                if s not in loc_strings:
                    print s
                    if 'citymapper' in s.lower():
                        print locs, comment['id']
                    if s.lower() == 'time on canada':
                        print locs, comment['id']
                    loc_strings.append(s)
            output_json.append({comment['id']:loc_strings})
            

    print(total, has_hit)
    for key in sorted(line_num_hit.keys()):
        print(key, line_num_hit[key])
        
    with open('July_2016_id_locations.json','w') as FH:
        json.dump(output_json, FH)
        
# def geocode_locs(json_file):
#     '''
#     for every entry in json
#     it will geocode all the locations
#     '''
#     with open(json_file) as FH:
#         json_data = json.load(FH)
#     output_json = []
#     seen_locs = set()
#     for entry in json_data:
#         locs = entry.values()[0]
#         for loc in locs:
#             loc = loc.lower()
#             if loc not in seen_locs:
#                 seen_locs.add(loc)
#                 tries = 0
#                 while tries < 10:
#                     g = geocoder.google(loc)
#                     if g.city:
#                         break
#                     time.sleep(tries)
#                     tries += 1
#                 if not any([g.city, g.state, g.country]):
#                     print 'could not get ', entry
#                     sys.exit()
#                 d = dict(city=g.city, state=g.state, country=g.country, latlng = g.latlng)
#                 new_entry = {loc:d}
#                 output_json.append(new_entry)
#                 with open('location_geocode.json', 'w') as FHOUT:
#                     json.dump(output_json, FHOUT)
            
#geocode_locs('id_locations.json')
#check_locations('July_2016_comments.json')

