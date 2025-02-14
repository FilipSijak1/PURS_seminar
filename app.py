from flask import Flask, request, redirect, url_for, render_template, session, make_response, jsonify
from flask import g
import MySQLdb
from hashlib import sha256
import requests
import paho.mqtt.client as mqtt
import json
from database.queries import LOGIN_QUERY, REGISTER_QUERY, SAVE_LOCATION_QUERY, DELETE_LOCATION_QUERY, GET_LOCATION_QUERY, CHECK_EMAIL_QUERY, CHECK_USERNAME_QUERY
from logging_config import setup_logging

app = Flask("app")
app.secret_key = '_5#y2L"F4Q8z-n-xec]//'

# logging setup
app.logger, script_logger = setup_logging()

# MQTT setup
mqtt_broker = "192.168.0.52"
mqtt_port = 1883
sensor_data_topic = "sensor/data"
watering_status_topic = "control/watering_status"

mqtt_client = mqtt.Client()

moisture_level = None
water_level = None
watering_status = None

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    app.logger.info(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(sensor_data_topic)

# Callback for received messages
def on_message(client, userdata, msg):
    global moisture_level, water_level
    if msg.topic == sensor_data_topic:
        data = msg.payload.decode().split(',')
        moisture_level = int(data[0])
        water_level = int(data[1])
        with app.app_context():
            user_id = session.get('user_id')  # Get the user_id from the session
            check_conditions_and_publish(user_id)

# Function to check conditions and publish the watering status
def check_conditions_and_publish(user_id):
    global moisture_level, water_level, watering_status
    if moisture_level is not None and water_level is not None:
        # Create a new database connection and cursor
        connection = MySQLdb.connect(host="localhost", user="app", passwd="1234", db="app")
        cursor = connection.cursor()
        try:
            weather_ok = fetchWeatherForSavedLocation(cursor, user_id)
            mqtt_ok = checkMQTTDataAndWater()
            new_watering_status = "true" if weather_ok and mqtt_ok else "false"
            if new_watering_status != watering_status:
                watering_status = new_watering_status
                mqtt_client.publish(watering_status_topic, watering_status)
                app.logger.info(f"Watering status changed to: {watering_status}")
        finally:
            cursor.close()
            connection.close()

# Example function to fetch weather for saved location
def fetchWeatherForSavedLocation(cursor, user_id):
    try:
        cursor.execute(GET_LOCATION_QUERY, (user_id,))
        location = cursor.fetchone()
        app.logger.info(f"Fetched location for user_id: {user_id} - {location}")

        if location:
            location = location[0]  # Assume there is only one saved location per user
            APIKey = 'f48314147c7960704569a1010beefbdb'
            fetch_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&units=metric&appid={APIKey}"
            # Fetch weather data for the saved location
            response = requests.get(fetch_url)
            weather_data = response.json()
            app.logger.info(f"Weather data fetched: {weather_data}")

            # Process weather data
            weather_condition = weather_data['weather'][0]['main']
            temperature = weather_data['main']['temp']

            # Check weather conditions
            if weather_condition in ['Clouds', 'Rain'] or temperature < 10 or temperature > 27:
                app.logger.info("Weather conditions not suitable for watering.")
                return False
            else:
                app.logger.info("Weather conditions suitable for watering.")
                return True
        else:
            app.logger.info("No location found for user.")
            return None
    except Exception as e:
        app.logger.error(f"Error fetching weather data: {str(e)}")
        return None

# Function to check MQTT data and decide on watering
def checkMQTTDataAndWater():
    global moisture_level, water_level
    try:
        # Check conditions
        if water_level < 25:
            return False
        elif moisture_level > 50:
            return False
        else:
            return True
    except Exception as e:
        app.logger.error(f"Error checking MQTT data: {str(e)}")
        return False

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

@app.teardown_request
def teardown_request_func(exception=None):
    if hasattr(g, 'cursor'):
        g.cursor.close()
    if hasattr(g, 'connection'):
        g.connection.close()

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

@app.get('/vremenska_prognoza')
def vremenska_prognoza():
    response = render_template('vremenska_prognoza.html')
    return response, 200

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('registration.html', title='Registracija')
    
    response = make_response()
    user_data = request.json  # Čitanje JSON podataka iz zahtjeva

    # Kopiramo user_data i uklanjamo lozinke za logiranje
    log_data = user_data.copy()
    log_data.pop('lozinka', None)
    log_data.pop('ponovljena_lozinka', None)
    app.logger.info(f"Received user data: {log_data}")

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
        # Provjera postojanja korisnika s unesenim korisničkim imenom
        g.cursor.execute(CHECK_USERNAME_QUERY, (username,))
        user = g.cursor.fetchone()

        if user:
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
                fetchWeatherForSavedLocation(g.cursor, user[0])

                return redirect(url_for('index'))
            else:
                response.data = 'Pogrešno korisničko ime ili lozinka'
                response.status_code = 401
        else:
            response.data = 'Korisnik ne postoji'
            response.status_code = 404
    except Exception as e:
        app.logger.error(f"Error during login: {str(e)}")
        response.data = f'Greška prilikom prijave: {str(e)}'
        response.status_code = 500

    return response

@app.route('/update_weather', methods=['POST'])
def update_weather():
    response = make_response()
    weather_data = fetchWeatherForSavedLocation(g.cursor, session['user_id'])  # Pass the cursor to the function

    try:
        if weather_data:
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

@app.route('/get_sensor_data')
def get_sensor_data():
    return jsonify({
        'moisture_level': moisture_level,
        'water_level': water_level
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
