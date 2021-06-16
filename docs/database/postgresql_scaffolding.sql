-- create database
CREATE DATABASE amy WITH OWNER postgres;

-- create database user (read/write)
CREATE USER amy WITH
    LOGIN
    PASSWORD 'secret password'
    NOSUPERUSER
    INHERIT
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    VALID UNTIL 'infinity';

-- create database user (read/only)
CREATE USER amy_ro WITH
    LOGIN
    PASSWORD 'secret password'
    NOSUPERUSER
    INHERIT
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    VALID UNTIL 'infinity';

-- roles and permissions
GRANT TEMPORARY ON DATABASE amy TO amy;
GRANT TEMPORARY ON DATABASE amy TO amy_ro;
GRANT ALL ON DATABASE amy TO postgres;
GRANT amy TO postgres;
GRANT amy_ro TO postgres;

-- run in `amy` database
GRANT ALL ON SCHEMA public TO amy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES to amy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES to amy;

GRANT USAGE ON SCHEMA public TO amy_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO amy_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO amy_ro;
-- the `FOR USER amy` means that when user `amy` creates tables
-- then by default amy_ro will have SELECT powers on them
ALTER DEFAULT PRIVILEGES FOR USER amy IN SCHEMA public GRANT SELECT ON TABLES TO amy_ro;
ALTER DEFAULT PRIVILEGES FOR USER amy IN SCHEMA public GRANT SELECT ON SEQUENCES to amy_ro;
