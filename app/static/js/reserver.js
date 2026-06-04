document.addEventListener('DOMContentLoaded', () => {
    // Éléments DOM
    const calendarDays = document.getElementById('calendarDays');
    const allerDisplay = document.getElementById('allerDisplay');
    const retourDisplay = document.getElementById('retourDisplay');
    const btnContinue = document.getElementById('btnContinue');
    
    // Inputs & Dropdowns
    const inputDepart = document.getElementById('inputDepart');
    const dropdownDepart = document.getElementById('dropdownDepart');
    const inputArrivee = document.getElementById('inputArrivee');
    const dropdownArrivee = document.getElementById('dropdownArrivee');
    const selectTypeVol = document.getElementById('selectTypeVol');
    
    // Récupération des données serveur (Jinja) transférées via HTML
    const flightSearchData = document.getElementById('flightSearchData');
    const aeroports = [];
    document.querySelectorAll('.airport-data').forEach(el => {
        aeroports.push({
            iata: el.dataset.iata,
            city: el.dataset.city
        });
    });

    // Passagers Dropdown
    const passengerDropdown = document.getElementById('passengerDropdown');
    const btnMinusPassenger = document.getElementById('btnMinusPassenger');
    const btnPlusPassenger = document.getElementById('btnPlusPassenger');
    const passengerCountText = document.getElementById('passengerCountText');
    const passengerCountDisplay = document.getElementById('passengerCountDisplay');
    let passengerCount = 1;

    // Resume Elements
    const iataDepart = document.getElementById('iataDepart');
    const cityDepart = document.getElementById('cityDepart');
    const iataArrivee = document.getElementById('iataArrivee');
    const cityArrivee = document.getElementById('cityArrivee');

    // Form inputs cachés
    const formDepart = document.getElementById('formDepart');
    const formArrivee = document.getElementById('formArrivee');
    const formTypeVol = document.getElementById('formTypeVol');
    const formPassagers = document.getElementById('formPassagers');
    const formDateAller = document.getElementById('formDateAller');
    const formDateRetour = document.getElementById('formDateRetour');

    // État du calendrier
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Réinitialise l'heure pour comparer uniquement les dates
    let startDate = null;
    let endDate = null;
    
    let savedSearchParams = null;
    if (flightSearchData && flightSearchData.dataset.searchParams && flightSearchData.dataset.searchParams !== 'null') {
        savedSearchParams = JSON.parse(flightSearchData.dataset.searchParams);
    }

    // Restauration des paramètres de session si existants
    if (savedSearchParams) {
        if (savedSearchParams.date_aller) startDate = new Date(savedSearchParams.date_aller + "T00:00:00");
        if (savedSearchParams.date_retour) endDate = new Date(savedSearchParams.date_retour + "T00:00:00");
        
        // Failsafe au cas où les dates seraient inversées dans la session
        if (startDate && endDate && startDate > endDate) {
            endDate = new Date(startDate);
        }
        
        if (savedSearchParams.passagers) passengerCount = parseInt(savedSearchParams.passagers);
    }

    let currentDate = startDate ? new Date(startDate.getFullYear(), startDate.getMonth(), 1) : new Date(today.getFullYear(), today.getMonth(), 1); 

    function renderCalendar() {
        const weekdays = `<div class="weekday">LUN</div><div class="weekday">MAR</div><div class="weekday">MER</div><div class="weekday">JEU</div><div class="weekday">VEN</div><div class="weekday">SAM</div><div class="weekday">DIM</div>`;
        calendarDays.innerHTML = weekdays;

        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        const monthNames = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];
        document.getElementById('monthYearDisplay').innerText = `${monthNames[month]} ${year}`;

        // Calcul du premier jour du mois (Ajustement pour que Lundi soit le 1er jour)
        let firstDayIndex = new Date(year, month, 1).getDay();
        const startOffset = firstDayIndex === 0 ? 6 : firstDayIndex - 1; 
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // Cases vides pour le début du mois
        for (let i = 0; i < startOffset; i++) {
            calendarDays.innerHTML += `<div class="day disabled" style="color: transparent;">0</div>`;
        }

        // Génération des jours
        for (let i = 1; i <= daysInMonth; i++) {
            const dateVal = new Date(year, month, i);
            
            // Griser les jours passés de manière dynamique
            const isDisabled = dateVal < today ? 'disabled' : '';
            
            const dayEl = document.createElement('div');
            dayEl.className = `day ${isDisabled}`;
            dayEl.dataset.date = dateVal.toISOString();
            dayEl.innerText = i;

            if (!isDisabled) {
                dayEl.addEventListener('click', () => handleDayClick(dateVal, dayEl));
            }
            calendarDays.appendChild(dayEl);
        }
        updateSelectionUI();
    }

    function handleDayClick(date, el) {
        const isOneWay = selectTypeVol.value === 'AS';

        if (isOneWay) {
            startDate = date;
            endDate = null;
        } else {
            if (!startDate || (startDate && endDate)) {
                // Nouvelle sélection
                startDate = date;
                endDate = null;
            } else if (date < startDate) {
                // Clic avant la date de début : on inverse intelligemment pour créer une plage
                endDate = startDate;
                startDate = date;
            } else {
                // Sélection de la date de fin
                endDate = date;
            }
        }
        updateSelectionUI();
    }

    function updateSelectionUI() {
        // Mise à jour visuelle du calendrier (Effet Pilule)
        document.querySelectorAll('.day').forEach(el => {
            if(el.classList.contains('disabled')) return;
            
            const elDate = new Date(el.dataset.date);
            el.classList.remove('selected', 'in-range', 'range-start', 'range-end');

            if (startDate && elDate.getTime() === startDate.getTime()) {
                el.classList.add('selected');
                if (endDate) el.classList.add('range-start');
            }
            
            if (endDate && elDate.getTime() === endDate.getTime()) {
                el.classList.add('selected', 'range-end');
            }
            
            if (startDate && endDate && elDate > startDate && elDate < endDate) {
                el.classList.add('in-range');
            }
        });

        // Mise à jour du texte de la carte résumé
        const formatDate = (d) => {
            const str = d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });
            return str.charAt(0).toUpperCase() + str.slice(1);
        };
        
        allerDisplay.innerText = startDate ? formatDate(startDate) : 'Sélectionnez une date';
        
        const isOneWay = selectTypeVol.value === 'AS';
        const retourBox = document.getElementById('retourDisplay').parentElement;

        if (isOneWay) {
            retourDisplay.innerText = 'Pas de retour';
            retourBox.style.opacity = '0.4';
        } else {
            retourDisplay.innerText = endDate ? formatDate(endDate) : 'Sélectionnez une date';
            retourBox.style.opacity = '1';
        }
        
        // --- Validation: Empêcher le même aéroport d'origine et destination ---
        const isSameAirport = (formDepart.value === formArrivee.value) && formDepart.value !== '';
        inputArrivee.style.borderColor = isSameAirport ? 'red' : '#E5E5EA';
        inputDepart.style.borderColor = isSameAirport ? 'red' : '#E5E5EA';

        // Mise à jour des inputs cachés pour le backend (Correction Fuseau Horaire)
        const getLocalISODate = (d) => {
            const offset = d.getTimezoneOffset() * 60000;
            return new Date(d.getTime() - offset).toISOString().split('T')[0];
        };

        if (startDate) formDateAller.value = getLocalISODate(startDate);
        if (endDate) formDateRetour.value = getLocalISODate(endDate);
        else formDateRetour.value = '';

        // Activation du bouton selon le type de vol
        if (isOneWay) {
            if (startDate && !isSameAirport) btnContinue.removeAttribute('disabled');
            else btnContinue.setAttribute('disabled', 'true');
        } else {
            if (startDate && endDate && !isSameAirport) btnContinue.removeAttribute('disabled');
            else btnContinue.setAttribute('disabled', 'true');
        }
    }

    // --- AUTOCOMPLETE POUR AÉROPORTS ---
    function renderSuggestions(filtered, dropdown, input, hidden, iataDisp, cityDisp) {
        dropdown.innerHTML = '';
        if (filtered.length === 0) {
            dropdown.style.display = 'none';
            return;
        }
        filtered.forEach(ap => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            div.innerHTML = `${ap.city} <span class="autocomplete-iata">${ap.iata}</span>`;
            div.addEventListener('mousedown', (e) => {
                // mousedown s'exécute avant le blur de l'input
                e.preventDefault(); 
                input.value = `${ap.city} (${ap.iata})`;
                hidden.value = ap.iata;
                iataDisp.innerText = ap.iata;
                cityDisp.innerText = ap.city;
                dropdown.style.display = 'none';
                updateSelectionUI();
            });
            dropdown.appendChild(div);
        });
        dropdown.style.display = 'block';
    }

    function initAutocomplete(input, dropdown, hidden, iataDisp, cityDisp, defaultIata) {
        const initialAp = aeroports.find(a => a.iata === hidden.value) || aeroports.find(a => a.iata === defaultIata);
        if (initialAp) {
            input.value = `${initialAp.city} (${initialAp.iata})`;
            hidden.value = initialAp.iata;
            iataDisp.innerText = initialAp.iata;
            cityDisp.innerText = initialAp.city;
        }

        input.addEventListener('focus', () => {
            input.select();
            renderSuggestions(aeroports, dropdown, input, hidden, iataDisp, cityDisp);
        });

        input.addEventListener('input', (e) => {
            const val = e.target.value.toLowerCase();
            const filtered = aeroports.filter(a => 
                a.city.toLowerCase().includes(val) || 
                a.iata.toLowerCase().includes(val)
            );
            renderSuggestions(filtered, dropdown, input, hidden, iataDisp, cityDisp);
        });

        input.addEventListener('blur', () => {
            // Rétablir la valeur sélectionnée si l'utilisateur n'a rien cliqué
            const ap = aeroports.find(a => a.iata === hidden.value);
            if (ap) {
                input.value = `${ap.city} (${ap.iata})`;
            }
            dropdown.style.display = 'none';
        });
    }

    initAutocomplete(inputDepart, dropdownDepart, formDepart, iataDepart, cityDepart, 'CDG');
    initAutocomplete(inputArrivee, dropdownArrivee, formArrivee, iataArrivee, cityArrivee, 'FCO');

    // --- SYNCHRONISATION DU TYPE DE VOL ---
    
    selectTypeVol.addEventListener('change', (e) => {
        formTypeVol.value = e.target.value;
        // Réinitialiser les dates et l'UI du calendrier lors d'un changement
        startDate = null;
        endDate = null;
        updateSelectionUI();
    });

    // --- OUVERTURE/FERMETURE DU DROPDOWN PASSAGERS ---
    const dropdownTrigger = passengerDropdown.querySelector('.dropdown-trigger button');
    dropdownTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        passengerDropdown.classList.toggle('is-active');
    });

    document.addEventListener('click', (e) => {
        if (!passengerDropdown.contains(e.target)) {
            passengerDropdown.classList.remove('is-active');
        }
    });

    // --- GESTION DES PASSAGERS ---
    btnPlusPassenger.addEventListener('click', (e) => {
        e.stopPropagation();
        if (passengerCount < 9) { // Limite optionnelle à 9 passagers max
            passengerCount++;
            passengerCountText.innerText = passengerCount;
            passengerCountDisplay.innerText = passengerCount;
            formPassagers.value = passengerCount;
        }
    });

    btnMinusPassenger.addEventListener('click', (e) => {
        e.stopPropagation();
        if (passengerCount > 1) {
            passengerCount--;
            passengerCountText.innerText = passengerCount;
            passengerCountDisplay.innerText = passengerCount;
            formPassagers.value = passengerCount;
        }
    });

    // --- INITIALISATION AU CHARGEMENT DE LA PAGE ---

    renderCalendar();
});