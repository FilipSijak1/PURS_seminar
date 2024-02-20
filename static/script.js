function submitForm() {
    var form = document.getElementById("locationForm");
    var formData = new FormData(form);
    var location = formData.get("Lokacija");

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/save_location");
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onload = function() {
        if (xhr.status === 201) {
            alert(xhr.responseText);
            fetchWeatherPeriodically(location); // Pozivamo funkciju za automatsko dohvaćanje vremenskih podataka
        } else {
            alert("Neuspješan unos lokacije: " + xhr.responseText);
        }
    };
    xhr.send(JSON.stringify({ "Lokacija": location }));
}

function fetchWeatherPeriodically(location) {
    getWeather(location); // Pozivamo funkciju za dohvaćanje vremenskih podataka
    setInterval(function() {
        getWeather(location); // Pozivamo funkciju za dohvaćanje vremenskih podataka svakih sat vremena
    }, 3600000); // 3600000 milisekundi = 1 sat
}

function getWeather(location) {
    var apiKey = 'f48314147c7960704569a1010beefbdb';
    var url = 'https://api.openweathermap.org/data/2.5/weather?q=' + location + '&appid=' + apiKey;

    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.onload = function () {
        if (xhr.status === 200) {
            var weatherData = JSON.parse(xhr.responseText);
            console.log(weatherData); // Ispisujemo podatke o vremenskoj prognozi u konzoli

            // Pozivamo funkciju za slanje podataka o vremenskoj prognozi na Flask aplikaciju
            sendWeatherDataToFlask(weatherData);
        } else {
            console.error('Neuspješan zahtjev. Status: ' + xhr.status);
        }
    };
    xhr.send();
}

function sendWeatherDataToFlask(weatherData) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/update_weather");
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onload = function() {
        if (xhr.status === 200) {
            console.log(xhr.responseText);
        } else {
            console.error("Neuspješno ažuriranje vremenskih podataka: " + xhr.responseText);
        }
    };
    xhr.send(JSON.stringify(weatherData));
}

let menu = document.querySelector('#menu-icon');
let navlist = document.querySelector('.navlist');
let sections = document.querySelectorAll('section');

menu.onclick = () => {
    menu.classList.toggle('bx-x');
    navlist.classList.toggle('open');
};
