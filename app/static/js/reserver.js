// app/static/js/reserver.js
// Extrait depuis reserver.html pour séparer le JS de l'HTML

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const calendarDays = document.getElementById('calendarDays');
    if (!calendarDays) return; // Ignore on non-reservation pages

    const allerDisplay = document.getElementById('allerDisplay');
    const retourDisplay = document.getElementById('retourDisplay');
    const priceDisplay = document.getElementById('priceDisplay');
    const btnContinue = document.getElementById('btnContinue');

    // Selects
    const selectDepart = document.getElementById('selectDepart');
    const selectArrivee = document.getElementById('selectArrivee');
    const selectPassagers = document.getElementById('selectPassagers');
    const selectClasse = document.getElementById('selectClasse');

    // Resume Elements
    const resumeItineraire = document.getElementById('resumeItineraire');
    const resumeClasse = document.getElementById('resumeClasse');
    const resumePassagers = document.getElementById('resumePassagers');

    // State
    let currentDate = new Date(2026, 5, 1); // Juin 2026
    let startDate = null;
    let endDate = null;

    // Générateur de prix qui prend en compte la CLASSE choisie
    const getPriceForDay = (dayIndex) => {
        const classMultiplier = parseFloat(selectClasse.value); // 1 (Eco), 2.5 (Biz), 4 (First)
        
        // On utilise une graine basée sur le jour pour que le prix d'un jour donné reste le même
        const pseudoRandom = Math.sin(dayIndex) * 10000;
        const fluctuation = Math.abs(Math.floor((pseudoRandom - Math.floor(pseudoRandom)) * 60));
        
        const basePrice = 45;
        return Math.floor((basePrice + fluctuation) * classMultiplier);
    };

    function renderCalendar() {
        const weekdays = `<div class="weekday">LUN</div><div class="weekday">MAR</div><div class="weekday">MER</div><div class="weekday">JEU</div><div class="weekday">VEN</div><div class="weekday">SAM</div><div class="weekday">DIM</div>`;
        calendarDays.innerHTML = weekdays;

        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        const monthNames = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];
        document.getElementById('monthYearDisplay').innerText = `${monthNames[month]} ${year}`;

        const firstDayIndex = new Date(year, month, 1).getDay();
        const startOffset = firstDayIndex === 0 ? 6 : firstDayIndex - 1; 
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // Cases vides
        for (let i = 0; i < startOffset; i++) {
            calendarDays.innerHTML += `<div class="day disabled"></div>`;
        }

        // Génération des jours
        for (let i = 1; i <= daysInMonth; i++) {
            const dateVal = new Date(year, month, i);
            const price = getPriceForDay(i + month*30); // Prix stable
            
            // Griser avant le 10 Juin 2026
            const isDisabled = i < 10 && month === 5 ? 'disabled' : '';
            
            const dayEl = document.createElement('div');
            dayEl.className = `day ${isDisabled}`;
            dayEl.dataset.date = dateVal.toISOString();
            dayEl.dataset.price = price;
            
            dayEl.innerHTML = `
                <span class="day-number">${i}</span>
                <span class="day-price">${price}€</span>
            `;

            if (!isDisabled) {
                dayEl.addEventListener('click', () => handleDayClick(dateVal, price, dayEl));
            }
            calendarDays.appendChild(dayEl);
        }
        updateSelectionUI();
    }

    function handleDayClick(date, price, el) {
        if (!startDate || (startDate && endDate)) {
            startDate = { date: date, price: price };
            endDate = null;
        } else if (date < startDate.date) {
            startDate = { date: date, price: price };
        } else {
            endDate = { date: date, price: price };
        }
        updateSelectionUI();
    }

    function updateSelectionUI() {
        document.querySelectorAll('.day').forEach(el => {
            if(el.classList.contains('disabled')) return;
            
            const elDate = new Date(el.dataset.date);
            el.classList.remove('selected', 'in-range', 'range-start', 'range-end');

            if (startDate && elDate.getTime() === startDate.date.getTime()) {
                el.classList.add('selected');
                if (endDate) el.classList.add('range-start');
            }
            
            if (endDate && elDate.getTime() === endDate.date.getTime()) {
                el.classList.add('selected', 'range-end');
            }
            
            if (startDate && endDate && elDate > startDate.date && elDate < endDate.date) {
                el.classList.add('in-range');
            }
        });

        const formatDate = (d) => d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
        
        allerDisplay.innerText = startDate ? formatDate(startDate.date) : '--';
        retourDisplay.innerText = endDate ? formatDate(endDate.date) : '--';
        
        const nbPassagers = parseInt(selectPassagers.value);

        if (startDate && endDate) {
            const totalPrixVol = parseInt(startDate.price) + parseInt(endDate.price);
            priceDisplay.innerText = `${totalPrixVol * nbPassagers} €`;
            btnContinue.removeAttribute('disabled');
        } else if (startDate) {
            priceDisplay.innerText = `dès ${parseInt(startDate.price) * nbPassagers} €`;
            btnContinue.setAttribute('disabled', 'true');
        } else {
            priceDisplay.innerText = '-- €';
            btnContinue.setAttribute('disabled', 'true');
        }
    }

    function updateSummaryPanel() {
        const dep = selectDepart.value.split(' ')[0]; // Récupère juste "Paris"
        const arr = selectArrivee.value.split(' ')[0];
        resumeItineraire.innerHTML = `${dep} <i class="fas fa-arrow-right mx-2 is-size-6" style="color: var(--accent);"></i> ${arr}`;
        
        resumeClasse.innerText = selectClasse.options[selectClasse.selectedIndex].text;
        
        const pax = selectPassagers.value;
        resumePassagers.innerText = `(${pax} Passager${pax > 1 ? 's' : ''})`;
        
        // Re-render calendrier pour mettre à jour les prix si la classe change
        renderCalendar(); 
    }

    // Event Listeners
    document.getElementById('prevMonth').addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth() - 1); renderCalendar(); });
    document.getElementById('nextMonth').addEventListener('click', () => { currentDate.setMonth(currentDate.getMonth() + 1); renderCalendar(); });

    document.getElementById('btnResetDates').addEventListener('click', () => { startDate = null; endDate = null; updateSelectionUI(); });

    // Update dynamique quand on touche au formulaire de recherche
    selectDepart.addEventListener('change', updateSummaryPanel);
    selectArrivee.addEventListener('change', updateSummaryPanel);
    selectPassagers.addEventListener('change', updateSummaryPanel);
    selectClasse.addEventListener('change', updateSummaryPanel); // Ceci déclenche un recalcul des prix !

    // Navigation vers l'étape suivante
    btnContinue.addEventListener('click', () => {
        // En production, on pourrait sauvegarder les choix dans la session via une requête fetch POST
        window.location.href = '/client/booking-flights';
    });

    // Initialisation
    updateSummaryPanel();
});