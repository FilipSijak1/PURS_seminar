function closeAlert() {
    const weatherAlert = document.getElementById('weather-alert');
    weatherAlert.style.display = 'none';
}

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
        logEvent(`Weather API response: ${JSON.stringify(json)}`);
        console.log(json.weather[0].main);
        const image = document.querySelector('.weather-box .weather-icon');
        const temperature = document.querySelector('.weather-box .temperature');
        const description = document.querySelector('.weather-box .description');
        const location = document.querySelector('.weather-box .location'); // New line to select location element
        const weatherAlert = document.getElementById('weather-alert'); // Select the weather alert element

        const currentTime = json.dt + json.timezone; // Adjust current time with timezone
        const sunrise = json.sys.sunrise + json.timezone; // Adjust sunrise time with timezone
        const sunset = json.sys.sunset + json.timezone; // Adjust sunset time with timezone
        const isNight = currentTime < sunrise || currentTime > sunset;

        switch (json.weather[0].main) {
            case 'Clear':
                image.src = isNight ? '/static/mjesec.png' : '/static/sunce.png';
                description.textContent = isNight ? 'Noć' : 'Sunčano';
                weatherAlert.style.display = 'none'; // Hide alert for clear weather
                break;

            case 'Rain':
                image.src = isNight ? '/static/noc_kisa.png' : '/static/kisa.png';
                description.textContent = 'Kišovito';
                weatherAlert.style.display = 'block'; // Show alert for rainy weather
                break;

            case 'Clouds':
                image.src = isNight ? '/static/noc_oblak.png' : '/static/oblak.png';
                description.textContent = 'Oblačno';
                weatherAlert.style.display = 'block'; // Show alert for cloudy weather
                break;

            case 'Wind':
                image.src = isNight ? '/static/noc_vjetar.png' : '/static/vjetar.png';
                description.textContent = 'Vjetrovito';
                weatherAlert.style.display = 'none'; // Hide alert for windy weather
                break;

            default:
                image.src = isNight ? '/static/weather_unknown.png' : '/static/weather_unknown.png';
                description.textContent = 'Nepoznato';
                weatherAlert.style.display = 'none'; // Hide alert for unknown weather
        }

        temperature.innerHTML = `${Math.round(json.main.temp)}<span>°C</span>`;
        location.textContent = city.charAt(0).toUpperCase() + city.slice(1); // Set the location with first letter capitalized

        // Spremi lokaciju u bazu podataka nakon što dobijemo odgovor o vremenu
        saveLocation(city);
    })
    .catch(error => {
        console.error('Error fetching weather data:', error);
        logEvent(`Error fetching weather data: ${error}`);
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
            logEvent('Lokacija uspješno spremljena');
        } else {
            console.error('Greška prilikom spremanja lokacije:', response.statusText);
            logEvent(`Greška prilikom spremanja lokacije: ${response.statusText}`);
        }
    })
    .catch(error => {
        console.error('Greška prilikom slanja zahtjeva:', error);
        logEvent(`Greška prilikom slanja zahtjeva: ${error}`);
    });
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
            const image = document.querySelector('.weather-box .weather-icon');
            const temperature = document.querySelector('.weather-box .temperature');
            const description = document.querySelector('.weather-box .description');
            const location = document.querySelector('.weather-box .location'); // New line to select location element
            const weatherAlert = document.getElementById('weather-alert'); // Select the weather alert element

            const currentTime = json.dt + json.timezone; // Adjust current time with timezone
            const sunrise = json.sys.sunrise + json.timezone; // Adjust sunrise time with timezone
            const sunset = json.sys.sunset + json.timezone; // Adjust sunset time with timezone
            const isNight = currentTime < sunrise || currentTime > sunset;

            switch (json.weather[0].main) {
                case 'Clear':
                    image.src = isNight ? '/static/mjesec.png' : '/static/sunce.png';
                    description.textContent = isNight ? 'Noć' : 'Sunčano';
                    weatherAlert.style.display = 'none'; // Hide alert for clear weather
                    break;

                case 'Rain':
                    image.src = isNight ? '/static/noc_kisa.png' : '/static/kisa.png';
                    description.textContent = 'Kišovito';
                    weatherAlert.style.display = 'block'; // Show alert for rainy weather
                    break;

                case 'Clouds':
                    image.src = isNight ? '/static/noc_oblak.png' : '/static/oblak.png';
                    description.textContent = 'Oblačno';
                    weatherAlert.style.display = 'block'; // Show alert for cloudy weather
                    break;

                case 'Wind':
                    image.src = isNight ? '/static/noc_vjetar.png' : '/static/vjetar.png';
                    description.textContent = 'Vjetrovito';
                    weatherAlert.style.display = 'none'; // Hide alert for windy weather
                    break;

                default:
                    image.src = isNight ? '/static/weather_unknown.png' : '/static/weather_unknown.png';
                    description.textContent = 'Nepoznato';
                    weatherAlert.style.display = 'none'; // Hide alert for unknown weather
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

// Funkcija za generiranje dummy podataka i ažuriranje statusa zalijevanja
function generateDummyData() {
    const wateringStatus = Math.random() > 0.5 ? 'true' : 'false';
    console.log('Generated watering status:', wateringStatus); // Dodano za debugiranje
    updateWateringStatus(wateringStatus);

    // Generiranje dummy podataka za vizualizaciju stupaca
    const humidityValue = Math.floor(Math.random() * 101); // Generiranje slučajnog broja od 0 do 100 za vlažnost tla
    const waterLevelValue = Math.floor(Math.random() * 101); // Generiranje slučajnog broja od 0 do 100 za razinu vode
    updateProgressBars(humidityValue, waterLevelValue);
    checkWaterLevel(waterLevelValue); // Provjera razine vode
}

// Funkcija za ažuriranje statusa zalijevanja
function updateWateringStatus(status) {
    const wateringAlert = document.getElementById('watering-alert');
    console.log('Updating watering status to:', status); // Dodano za debugiranje
    if (status === 'true') {
        wateringAlert.style.display = 'block';
    } else {
        wateringAlert.style.display = 'none';
    }
}

// Funkcija za ažuriranje progresnih traka
function updateProgressBars(humidity, waterLevel) {
    const humidityBar = document.getElementById('humidity-bar');
    const humidityValueText = document.getElementById('humidity-value');
    const waterLevelBar = document.getElementById('water-level-bar');
    const waterLevelValueText = document.getElementById('water-level-value');

    humidityBar.style.height = `${humidity}%`;
    humidityValueText.textContent = `${humidity}%`;

    waterLevelBar.style.height = `${waterLevel}%`;
    waterLevelValueText.textContent = `${waterLevel}%`;
}

// Funkcija za provjeru razine vode i prikaz skočne poruke
function checkWaterLevel(waterLevel) {
    const waterAlert = document.getElementById('water-alert');
    if (waterLevel < 25) {
        waterAlert.style.display = 'block';
    } else {
        waterAlert.style.display = 'none';
    }
}

// Generiranje dummy podataka svakih 5 sekundi
setInterval(generateDummyData, 5000);

function logEvent(message) {
    fetch('/log_event', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message })
    });
}
