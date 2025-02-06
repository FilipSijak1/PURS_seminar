from flask import Flask, request, redirect, url_for, render_template, session, make_response, jsonify
from flask import g
import MySQLdb
from hashlib import sha256
import requests  # Dodali smo import za requests biblioteku
import paho.mqtt.publish as publish
import json
from database.queries import LOGIN_QUERY, REGISTER_QUERY, SAVE_LOCATION_QUERY, DELETE_LOCATION_QUERY, GET_LOCATION_QUERY, CHECK_EMAIL_QUERY, CHECK_USERNAME_QUERY
import logging
from logging.handlers import RotatingFileHandler
import os

app = Flask("app")
app.secret_key = '_5#y2L"F4Q8z-n-xec]//'

# Ensure the logs directory exists
logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Set up logging for app
app_log_file_path = os.path.join(logs_dir, 'app.log')
app_handler = RotatingFileHandler(app_log_file_path, maxBytes=10000, backupCount=1)
app_handler.setLevel(logging.INFO)
app_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_handler.setFormatter(app_formatter)
app.logger.addHandler(app_handler)
app.logger.setLevel(logging.INFO)  # Ensure the logger level is set

# Set up logging for script.js
script_log_file_path = os.path.join(logs_dir, 'script.log')
script_handler = RotatingFileHandler(script_log_file_path, maxBytes=10000, backupCount=1)
script_handler.setLevel(logging.INFO)
script_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
script_handler.setFormatter(script_formatter)
script_logger = logging.getLogger('scriptLogger')
script_logger.addHandler(script_handler)
script_logger.setLevel(logging.INFO)

@app.route('/log_event', methods=['POST'])
def log_event():
    data = request.json
    script_logger.info(f"Client log: {data['message']}")
    return '', 204

@app.route('/save_location', methods=['POST'])
def save_location():
    response = make_response()
    location_data = request.json
    app.logger.info(f"Received location data: {location_data}")

    try:
        # Delete the previous location from the database if it exists
        g.cursor.execute(DELETE_LOCATION_QUERY, (session['user_id'],))
        app.logger.info(f"Deleted previous location for user_id: {session['user_id']}")

        # Insert the new location into the database
        g.cursor.execute(SAVE_LOCATION_QUERY, (location_data['location'], session['user_id']))
        g.connection.commit()
        app.logger.info(f"Saved new location: {location_data['location']} for user_id: {session['user_id']}")

        response.data = 'Uspješno spremljena nova lokacija'
        response.status_code = 201
    except Exception as e:
        g.connection.rollback()
        app.logger.error(f"Error saving location: {str(e)}")
        response.data = f'Greška prilikom spremanja lokacije: {str(e)}'
        response.status_code = 500
    
    return response

# Example function to fetch weather for saved location
def fetchWeatherForSavedLocation():
    try:
        g.cursor.execute(GET_LOCATION_QUERY, (session['user_id'],))
        location = g.cursor.fetchone()
        app.logger.info(f"Fetched location for user_id: {session['user_id']} - {location}")

        if location:
            location = location[0]  # Assume there is only one saved location per user
            APIKey = 'f48314147c7960704569a1010beefbdb'
            fetch_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&units=metric&appid={APIKey}"
            # Fetch weather data for the saved location
            response = requests.get(fetch_url)
            weather_data = response.json()
            app.logger.info(f"Weather data fetched: {weather_data}")

            # Process weather data
            # You can add further processing or save it to the database here

            return weather_data
        else:
            app.logger.info("No location found for user.")
            return None
    except Exception as e:
        app.logger.error(f"Error fetching weather data: {str(e)}")
        return None

@app.before_request
def before_request_func():
    g.connection = MySQLdb.connect(host="localhost", user="app",
                                   passwd="1234", db="app")
    g.cursor = g.connection.cursor()
    if request.path.startswith('/static'):
        return  # Skip the login check for static files
    if request.path == '/login':
        return
    if session.get('username') is None and request.path != '/register':
        return redirect(url_for('login_page'))

@app.get('/')
def index():
    response = render_template('index.html')
    return response, 200

@app.get('/logout')
def logout():
    session.pop('username')
    return redirect(url_for('login_page'))

@app.get('/login')
def login_page():
    # Provjerava je li korisnik već prijavljen
    if 'username' in session:
        return redirect(url_for('index'))
    
    # Ako nije prijavljen, prikaži stranicu za prijavu
    response = render_template('login.html', title='Login stranica')
    return response

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('registration.html', title='Registracija')
    
    response = make_response()
    user_data = request.json  # Čitanje JSON podataka iz zahtjeva
    app.logger.info(f"Received user data: {user_data}")

    # Provjerava se jesu li svi potrebni podaci prisutni
    required_fields = ['ime', 'prezime', 'korisnicko_ime', 'lozinka', 'ponovljena_lozinka', 'email']
    if all(field in user_data for field in required_fields):
        # Provjera podudaranja lozinki
        if user_data['lozinka'] != user_data['ponovljena_lozinka']:
            response.data = 'Lozinke se ne podudaraju'
            response.status_code = 400
        else:
            try:
                # Provjera postojanja korisnika s istim emailom
                g.cursor.execute(CHECK_EMAIL_QUERY, (user_data['email'],))
                existing_email = g.cursor.fetchone()
                app.logger.info(f"Existing email: {existing_email}")

                # Provjera postojanja korisnika s istim korisničkim imenom
                g.cursor.execute(CHECK_USERNAME_QUERY, (user_data['korisnicko_ime'],))
                existing_username = g.cursor.fetchone()
                app.logger.info(f"Existing username: {existing_username}")

                if existing_email:
                    response.data = 'Korisnik s tom email adresom već postoji'
                    response.status_code = 400
                elif existing_username:
                    response.data = 'Korisnik s tim korisničkim imenom već postoji'
                    response.status_code = 400
                else:
                    # Izvršavanje SQL upita s podacima korisnika
                    hashed_lozinka = sha256(user_data['lozinka'].encode()).hexdigest()
                    app.logger.info(f"Hashed password: {hashed_lozinka}")
                    g.cursor.execute(REGISTER_QUERY, (user_data['ime'], user_data['prezime'], user_data['korisnicko_ime'], hashed_lozinka, user_data['email']))
                    g.connection.commit()
                    response.data = 'Uspješno ste registrirali korisnika'
                    response.status_code = 201
            except Exception as e:
                app.logger.error(f"Error during registration: {str(e)}")
                response.data = f'Greška prilikom registracije: {str(e)}'
                response.status_code = 500
    else:
        response.data = 'Nisu pruženi svi potrebni podaci'
        response.status_code = 400
    
    return response

@app.route('/login', methods=['POST'])
def login():
    response = make_response()
    username = request.form.get('korisnicko_ime')
    password = request.form.get('lozinka')

    try:
        # Hash the password for comparison
        hashed_password = sha256(password.encode()).hexdigest()
        app.logger.info(f"Executing query: {LOGIN_QUERY} with username: {username} and hashed password: {hashed_password}")

        g.cursor.execute(LOGIN_QUERY, (username, hashed_password))
        user = g.cursor.fetchone()

        # Debugging: Print the result from the database
        app.logger.info(f"Query result: {user}")

        if user:
            session['username'] = user[3]  # Save username in session
            session['user_id'] = user[0] 
            
            # Nakon prijave korisnika, automatski dohvatimo vremenske podatke za spremljenu lokaciju
            fetchWeatherForSavedLocation()

            return redirect(url_for('index'))
        else:
            response.data = 'Pogrešno korisničko ime ili lozinka'
            response.status_code = 401
    except Exception as e:
        app.logger.error(f"Error during login: {str(e)}")
        response.data = f'Greška prilikom prijave: {str(e)}'
        response.status_code = 500

    return response

@app.route('/update_weather', methods=['POST'])
def update_weather():
    response = make_response()
    weather_data = fetchWeatherForSavedLocation()  # Dohvaćanje vremenskih podataka pomoću funkcije fetchWeatherForSavedLocation

    try:
        # Ovdje možete izvršiti bilo kakvu željenu obradu podataka o vremenskoj prognozi
        # Na primjer, možete ih spremiti u bazu podataka, poslati na daljnju analizu itd.

        # Primjer spremanja podataka u bazu podataka:
        if weather_data:
            # Ovdje biste izvršili SQL upit za spremanje podataka o vremenskoj prognozi
            # Pretpostavljamo da imate bazu podataka već postavljenu
            # Na primjer, začasno ćemo ispisati podatke u konzoli
            print(weather_data)
            
            response.data = 'Podaci o vremenskoj prognozi su uspješno ažurirani'
            response.status_code = 200
        else:
            response.data = 'Podaci o vremenskoj prognozi nisu dostupni'
            response.status_code = 404
    except Exception as e:
        response.data = f'Greška prilikom ažuriranja podataka o vremenskoj prognozi: {str(e)}'
        response.status_code = 500
    
    return response

@app.route('/get_saved_location', methods=['GET'])
def get_saved_location():
    try:
        # Dohvati spremljenu lokaciju iz baze podataka
        g.cursor.execute(GET_LOCATION_QUERY, (session['user_id'],))
        location = g.cursor.fetchone()[0]  # Pretpostavljamo da postoji samo jedna spremljena lokacija po korisniku

        return jsonify({'location': location}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
