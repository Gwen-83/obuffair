document.addEventListener('DOMContentLoaded', () => {
    // Éléments DOM
    const calendarDays = document.getElementById('calendarDays');
    const allerDisplay = document.getElementById('allerDisplay');
    const retourDisplay = document.getElementById('retourDisplay');
    const btnContinue = document.getElementById('btnContinue');
    
    // Selects
    const selectDepart = document.getElementById('selectDepart');
    const selectArrivee = document.getElementById('selectArrivee');
    const selectClasse = document.getElementById('selectClasse');
    const selectTypeVol = document.getElementById('selectTypeVol');
    
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
    const formClasse = document.getElementById('formClasse');
    const formTypeVol = document.getElementById('formTypeVol');
    const formPassagers = document.getElementById('formPassagers');
    const formDateAller = document.getElementById('formDateAller');
    const formDateRetour = document.getElementById('formDateRetour');

    // État du calendrier
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Réinitialise l'heure pour comparer uniquement les dates
    let currentDate = new Date(today.getFullYear(), today.getMonth(), 1); 
    let startDate = null;
    let endDate = null;

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
                // Clic avant la date de début
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
        const optionsDate = { weekday: 'short', day: 'numeric', month: 'short' };
        const formatDate = (d) => d.toLocaleDateString('fr-FR', optionsDate);
        
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
        
        // Mise à jour des inputs cachés pour le backend
        if (startDate) formDateAller.value = startDate.toISOString().split('T')[0];
        if (endDate) formDateRetour.value = endDate.toISOString().split('T')[0];
        else formDateRetour.value = '';

        // Activation du bouton selon le type de vol
        if (isOneWay) {
            if (startDate) btnContinue.removeAttribute('disabled');
            else btnContinue.setAttribute('disabled', 'true');
        } else {
            if (startDate && endDate) btnContinue.removeAttribute('disabled');
            else btnContinue.setAttribute('disabled', 'true');
        }
    }

    // Extraction IATA et Ville depuis la balise select (ex: "Paris (CDG)")
    function extractLocation(str) {
        const parts = str.split('(');
        return {
            city: parts[0].trim(),
            iata: parts[1] ? parts[1].replace(')', '').trim() : ''
        };
    }

    function updateSummaryPanel() {
        // Mise à jour des IATA et villes Flighty Style
        // On récupère le texte visible de l'option sélectionnée (ex: "Paris (CDG)")
        const depText = selectDepart.options[selectDepart.selectedIndex].text;
        const arrText = selectArrivee.options[selectArrivee.selectedIndex].text;
        
        const dep = extractLocation(depText);
        const arr = extractLocation(arrText);
        
        iataDepart.innerText = selectDepart.value; // La value contient directement le code (ex: CDG)
        cityDepart.innerText = dep.city;
        formDepart.value = selectDepart.value;
        
        iataArrivee.innerText = selectArrivee.value;
        cityArrivee.innerText = arr.city;
        formArrivee.value = selectArrivee.value;
        
        formClasse.value = selectClasse.value;
        formTypeVol.value = selectTypeVol.value;
        formPassagers.value = passengerCount;
    }

    // Écouteurs d'événements
    document.getElementById('prevMonth').addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth() - 1); renderCalendar(); });
    document.getElementById('nextMonth').addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth() + 1); renderCalendar(); });
    document.getElementById('btnResetDates').addEventListener('click', () => { startDate = null; endDate = null; updateSelectionUI(); });

    selectDepart.addEventListener('change', updateSummaryPanel);
    selectArrivee.addEventListener('change', updateSummaryPanel);
    selectClasse.addEventListener('change', updateSummaryPanel);
    
    // Gestion du dropdown passagers
    passengerDropdown.querySelector('.dropdown-trigger button').addEventListener('click', (e) => {
        e.stopPropagation();
        passengerDropdown.classList.toggle('is-active');
    });

    document.addEventListener('click', (e) => {
        if (!passengerDropdown.contains(e.target)) {
            passengerDropdown.classList.remove('is-active');
        }
    });

    btnPlusPassenger.addEventListener('click', (e) => {
        e.stopPropagation();
        if (passengerCount < 9) {
            passengerCount++;
            updatePassengerUI();
        }
    });

    btnMinusPassenger.addEventListener('click', (e) => {
        e.stopPropagation();
        if (passengerCount > 1) {
            passengerCount--;
            updatePassengerUI();
        }
    });

    function updatePassengerUI() {
        passengerCountText.innerText = passengerCount;
        passengerCountDisplay.innerText = passengerCount;
        formPassagers.value = passengerCount;
        updateSummaryPanel();
    }
    
    selectTypeVol.addEventListener('change', () => {
        const isOneWay = selectTypeVol.value === 'AS';
        const typeVolIcon = document.getElementById('typeVolIcon');
        if (isOneWay) {
            typeVolIcon.className = 'fas fa-arrow-right';
        } else {
            typeVolIcon.className = 'fas fa-exchange-alt';
        }

        if (isOneWay && endDate) endDate = null; // Retire la date de retour si on passe en aller simple
        updateSummaryPanel();
        updateSelectionUI(); // Actualise l'affichage du calendrier
    });

    // Initialisation
    updateSummaryPanel();
    renderCalendar();
});