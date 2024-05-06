from flask import Flask, request, redirect, url_for, render_template, session, make_response, url_for, jsonify
from flask import g
import MySQLdb
from hashlib import sha256
import requests  # Dodali smo import za requests biblioteku
import paho.mqtt.publish as publish
import json

app = Flask("app")
app.secret_key = '_5#y2L"F4Q8z-n-xec]//'

# Definiramo funkciju fetchWeatherForSavedLocation
def fetchWeatherForSavedLocation():
    try:
        # Dohvati spremljenu lokaciju iz baze podataka
        query = "SELECT location FROM locations WHERE user_id = %s"
        g.cursor.execute(query, (session['user_id'],))
        location = g.cursor.fetchone()[0]  # Pretpostavljamo da postoji samo jedna spremljena lokacija po korisniku

        APIKey = 'f48314147c7960704569a1010beefbdb'
        fetch_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&units=metric&appid={APIKey}"
        
        # Dohvati podatke o vremenskoj prognozi za spremljenu lokaciju
        response = requests.get(fetch_url)
        weather_data = response.json()

        # Obrada podataka o vremenskoj prognozi
        # Ovdje možete dodati daljnju obradu podataka ili spremanje u bazu podataka

        return weather_data
    except Exception as e:
        print(f'Greška prilikom dohvaćanja vremenskih podataka: {str(e)}')
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
                check_email_query = "SELECT * FROM korisnik WHERE email = %s"
                g.cursor.execute(check_email_query, (user_data['email'],))
                existing_email = g.cursor.fetchone()

                # Provjera postojanja korisnika s istim korisničkim imenom
                check_username_query = "SELECT * FROM korisnik WHERE korisnicko_ime = %s"
                g.cursor.execute(check_username_query, (user_data['korisnicko_ime'],))
                existing_username = g.cursor.fetchone()

                if existing_email:
                    response.data = 'Korisnik s tom email adresom već postoji'
                    response.status_code = 400
                elif existing_username:
                    response.data = 'Korisnik s tim korisničkim imenom već postoji'
                    response.status_code = 400
                else:
                    # Čitanje sadržaja SQL datoteke
                    with app.open_resource('templates/registerUser.sql', mode='r') as file:
                        query = file.read()

                    # Izvršavanje SQL upita s podacima korisnika
                    g.cursor.execute(query, (user_data['ime'], user_data['prezime'], user_data['korisnicko_ime'], user_data['lozinka'], user_data['email']))
                    g.connection.commit()
                    response.data = 'Uspješno ste registrirali korisnika'
                    response.status_code = 201
            except Exception as e:
                response.data = f'Greška prilikom registracije: {str(e)}'
                response.status_code = 500
    else:
        response.data = 'Nisu pruženi svi potrebni podaci'
        response.status_code = 400
    
    return response

@app.post('/login')
def login():
    response = make_response()
    username = request.form.get('korisnicko_ime')
    password = request.form.get('lozinka')

    try:
        query = "SELECT * FROM korisnik WHERE korisnicko_ime = %s AND password = UNHEX(SHA2(%s, 256))"
        g.cursor.execute(query, (username, password))
        user = g.cursor.fetchone()

        if user:
            session['username'] = user[3] # Save username in session
            session['user_id'] = user[0] 
            
            # Nakon prijave korisnika, automatski dohvatimo vremenske podatke za spremljenu lokaciju
            fetchWeatherForSavedLocation()

            return redirect(url_for('index'))
        else:
            response.data = 'Pogrešno korisničko ime ili lozinka'
            response.status_code = 401
    except Exception as e:
        response.data = f'Greška prilikom prijave: {str(e)}'
        response.status_code = 500
    
    return response

@app.post('/save_location')
def save_location():
    response = make_response()
    location_data = request.json

    try:
        # Brišemo prethodnu lokaciju iz baze podataka ako postoji
        delete_query = "DELETE FROM locations WHERE user_id = %s"
        g.cursor.execute(delete_query, (session['user_id'],))

        # Unosimo novu lokaciju u bazu podataka
        insert_query = "INSERT INTO locations (user_id, location) VALUES (%s, %s)"
        g.cursor.execute(insert_query, (session['user_id'], location_data['location']))
        g.connection.commit()

        response.data = 'Uspješno spremljena nova lokacija'
        response.status_code = 201
    except Exception as e:
        response.data = f'Greška prilikom spremanja lokacije: {str(e)}'
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
        query = "SELECT location FROM locations WHERE user_id = %s"
        g.cursor.execute(query, (session['user_id'],))
        location = g.cursor.fetchone()[0]  # Pretpostavljamo da postoji samo jedna spremljena lokacija po korisniku

        return jsonify({'location': location}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
