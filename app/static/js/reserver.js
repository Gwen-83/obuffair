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
    
    // Resume Elements
    const iataDepart = document.getElementById('iataDepart');
    const cityDepart = document.getElementById('cityDepart');
    const iataArrivee = document.getElementById('iataArrivee');
    const cityArrivee = document.getElementById('cityArrivee');

    // Form inputs cachés
    const formDepart = document.getElementById('formDepart');
    const formArrivee = document.getElementById('formArrivee');
    const formClasse = document.getElementById('formClasse');
    const formDateAller = document.getElementById('formDateAller');
    const formDateRetour = document.getElementById('formDateRetour');

    // État du calendrier
    let currentDate = new Date(2026, 5, 1); // Juin 2026 pour la démo
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
            
            // Simulation : Griser les jours passés (avant le 10 Juin 2026)
            const isDisabled = i < 10 && month === 5 && year === 2026 ? 'disabled' : '';
            
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
        retourDisplay.innerText = endDate ? formatDate(endDate) : 'Sélectionnez une date';
        
        // Mise à jour des inputs cachés pour le backend
        if (startDate) formDateAller.value = startDate.toISOString().split('T')[0];
        if (endDate) formDateRetour.value = endDate.toISOString().split('T')[0];

        // Activation du bouton uniquement si l'aller-retour est sélectionné
        if (startDate && endDate) {
            btnContinue.removeAttribute('disabled');
        } else {
            btnContinue.setAttribute('disabled', 'true');
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
        const dep = extractLocation(selectDepart.value);
        const arr = extractLocation(selectArrivee.value);
        
        iataDepart.innerText = dep.iata;
        cityDepart.innerText = dep.city;
        formDepart.value = dep.iata;
        
        iataArrivee.innerText = arr.iata;
        cityArrivee.innerText = arr.city;
        formArrivee.value = arr.iata;
        
        formClasse.value = selectClasse.value;
    }

    // Écouteurs d'événements
    document.getElementById('prevMonth').addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth() - 1); renderCalendar(); });
    document.getElementById('nextMonth').addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth() + 1); renderCalendar(); });
    document.getElementById('btnResetDates').addEventListener('click', () => { startDate = null; endDate = null; updateSelectionUI(); });

    selectDepart.addEventListener('change', updateSummaryPanel);
    selectArrivee.addEventListener('change', updateSummaryPanel);
    selectClasse.addEventListener('change', updateSummaryPanel);

    // Initialisation
    updateSummaryPanel();
    renderCalendar();
});