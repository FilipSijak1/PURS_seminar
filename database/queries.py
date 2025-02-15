# Description: SQL queries for database operations

# SQL query for checking if user with the same email exists
CHECK_EMAIL_QUERY = """
SELECT * FROM korisnik WHERE email = %s
"""

# SQL query for checking if user with the same username exists
CHECK_USERNAME_QUERY = """
SELECT * FROM korisnik WHERE korisnicko_ime = %s
"""

# SQL query for user login
LOGIN_QUERY = """
SELECT * FROM korisnik WHERE korisnicko_ime = %s AND password = %s
"""

# SQL query for fetching saved locations
GET_LOCATION_QUERY = """
SELECT location FROM locations WHERE user_id = %s
"""

# SQL query for saving location
SAVE_LOCATION_QUERY = """
REPLACE INTO locations (user_id, location) VALUES (%s, %s)
"""

# SQL query for deleting location
DELETE_LOCATION_QUERY = """
DELETE FROM locations WHERE user_id = %s
"""

# SQL query for registering a new user
REGISTER_QUERY = """
INSERT INTO korisnik (ime, prezime, korisnicko_ime, password, email) VALUES (%s, %s, %s, %s, %s)
"""

# SQL query for fetching the user from the database
GET_USER_QUERY = """
SELECT * FROM korisnik WHERE
password = UNHEX(SHA2('{{passwd}}', 256))
AND korisnicko_ime = '{{user}}';
"""

# SQL query for checking if location exists for user
CHECK_LOCATION_EXISTS_QUERY = """
SELECT COUNT(*) FROM locations WHERE user_id = %s
"""

# SQL query for inserting new location
INSERT_LOCATION_QUERY = """
INSERT INTO locations (user_id, location) VALUES (%s, %s)
"""

# SQL query for updating existing location
UPDATE_LOCATION_QUERY = """
UPDATE locations SET location = %s WHERE user_id = %s
"""