-- PostgreSQL initialization script
-- This script runs automatically when PostgreSQL container starts for the first time

-- Create the main application database
CREATE DATABASE wowactuality;

-- Create the wowbot database (for legacy compatibility)
CREATE DATABASE wowbot;

-- Grant all privileges on both databases to the wowbot user
GRANT ALL PRIVILEGES ON DATABASE wowactuality TO wowbot;
GRANT ALL PRIVILEGES ON DATABASE wowbot TO wowbot;

-- Log the successful database creation
\echo 'Databases created successfully: wowactuality, wowbot'