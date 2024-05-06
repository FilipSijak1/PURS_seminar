const locationForm = document.getElementById('locationForm');

locationForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const APIKey = 'f48314147c7960704569a1010beefbdb';
    const city = document.querySelector('.search-box input').value;

    if (city === '')
        return;

    fetch(`https://api.openweathermap.org/data/2.5/weather?q=${city}&units=metric&appid=${APIKey}`)
    .then(response => response.json())
    .then(json => {
        console.log('Odgovor primljen:', json);
        console.log(json.weather[0].main);
        const image = document.querySelector('.weather-box .weather-icon');
        const temperature = document.querySelector('.weather-box .temperature');
        const description = document.querySelector('.weather-box .description');
        const location = document.querySelector('.weather-box .location'); // New line to select location element

        switch (json.weather[0].main) {
            case 'Clear':
                image.src = '/static/sunce.png';
                description.textContent = 'Sunčano';
                break;

            case 'Rain':
                image.src = '/static/kisa.png';
                description.textContent = 'Kišovito';
                break;

            case 'Clouds':
                image.src = '/static/oblak.png';
                description.textContent = 'Oblačno';
                break;

            default:
                image.src = '/static/oblak.png';
                description.textContent = 'Nepoznato';
        }

        temperature.innerHTML = `${Math.round(json.main.temp)}<span>°C</span>`;
        location.textContent = city.charAt(0).toUpperCase() + city.slice(1); // Set the location with first letter capitalized
    });
});

function saveLocation(location) {
    fetch('/save_location', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 'location': location })
    })
    .then(response => {
        if (response.ok) {
            console.log('Lokacija uspješno spremljena');
        } else {
            console.error('Greška prilikom spremanja lokacije:', response.statusText);
        }
    })
    .catch(error => console.error('Greška prilikom slanja zahtjeva:', error));
}

function fetchWeatherForSavedLocation() {
    fetch('/get_saved_location')
    .then(response => response.json())
    .then(data => {
        const savedLocation = data.location;
        const APIKey = 'f48314147c7960704569a1010beefbdb';

        fetch(`https://api.openweathermap.org/data/2.5/weather?q=${savedLocation}&units=metric&appid=${APIKey}`)
        .then(response => response.json())
        .then(json => {
            console.log('Odgovor primljen:', json);
            console.log(json.weather[0].main);
            const image = document.querySelector('.weather-box .weather-icon');
            const temperature = document.querySelector('.weather-box .temperature');
            const description = document.querySelector('.weather-box .description');
            const location = document.querySelector('.weather-box .location'); // New line to select location element

            switch (json.weather[0].main) {
                case 'Clear':
                    image.src = '/static/sunce.png';
                    description.textContent = 'Sunčano';
                    break;

                case 'Rain':
                    image.src = '/static/kisa.png';
                    description.textContent = 'Kišovito';
                    break;

                case 'Clouds':
                    image.src = '/static/oblak.png';
                    description.textContent = 'Oblačno';
                    break;

                default:
                    image.src = '/static/oblak.png';
                    description.textContent = 'Nepoznato';
            }

            temperature.innerHTML = `${Math.round(json.main.temp)}<span>°C</span>`;
            location.textContent = savedLocation.charAt(0).toUpperCase() + savedLocation.slice(1); // Set the location with first letter capitalized
        })
        .catch(error => console.error('Greška prilikom dohvaćanja vremenskih podataka:', error));
    })
    .catch(error => console.error('Greška prilikom dohvaćanja spremljene lokacije:', error));
}

setInterval(fetchWeatherForSavedLocation, 3600000); // 3600000 milisekundi = 1 sat

let menu = document.querySelector('#menu-icon');
let navlist = document.querySelector('.navlist');
let sections = document.querySelectorAll('section');

menu.onclick = () => {
    menu.classList.toggle('bx-x');
    navlist.classList.toggle('open');
};


// Pretplata na MQTT teme i ažuriranje progresnih traka
function subscribeToMQTTTopics() {
    // Pretplata na MQTT topic za vlagu
    // Ovdje zamijenite 'humidity-topic' sa stvarnim imenom MQTT topica za vlagu
    // i 'water-level-topic' sa stvarnim imenom MQTT topica za razinu vode
    const humidityTopic = 'humidity-topic';
    const waterLevelTopic = 'water-level-topic';

    // Simulacija pretplate na MQTT topice (možete zamijeniti s pravim MQTT klijentom)
    setInterval(() => {
        // Generiranje slučajnih vrijednosti za vlagu i razinu vode (simulacija primanja podataka s MQTT topica)
        const humidityValue = Math.floor(Math.random() * 101); // Generiranje slučajnog broja od 0 do 100 za vlagu
        const waterLevelValue = Math.floor(Math.random() * 101); // Generiranje slučajnog broja od 0 do 100 za razinu vode

        // Ažuriranje progresnih traka s novim podacima
        updateProgressBars(humidityValue, waterLevelValue);
    }, 5000); // Interval od 5 sekundi (možete prilagoditi prema potrebi)
}

// Poziv funkcije za pretplatu na MQTT topice i ažuriranje progresnih traka
subscribeToMQTTTopics();

