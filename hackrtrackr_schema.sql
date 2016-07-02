-- sqlite3 hackrtrackr.db < hackrtrackr_schema.sql

PRAGMA foreign_keys = ON;

--DROP TABLE if exists posts;
CREATE TABLE posts(
  comment_date DATE,
  company TEXT,
  glassdoor_id TEXT,
  id INTERGER,
  text TEXT,
  thread_date DATE,
  thread_id INTEGER
);

--DROP TABLE if exists company;
CREATE TABLE company(
  con_review TEXT,
  id INTEGER,
  industry TEXT,
  name TEXT,
  numberOfRatings TEXT,
  overallRating INTEGER,
  pro_review TEXT,
  squareLogo INTEGER,
  website TEXT
);

--DROP TABLE if exists id_geocode;
CREATE TABLE id_geocode(
  city TEXT,
  country TEXT,
  id INTEGER,
  lat FLOAT,
  lng FLOAT,
  state TEXT
);

