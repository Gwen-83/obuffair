document.addEventListener("DOMContentLoaded", () => {
    const dataElement = document.getElementById('bookingOptionsData');
    if (!dataElement) return;

    const avion = JSON.parse(dataElement.dataset.avion);
    const takenSeats = JSON.parse(dataElement.dataset.takenSeats);
    let currentClass = dataElement.dataset.currentClass;
    let pendingSeat = null;
    const prices = JSON.parse(dataElement.dataset.prices);
    
    const container = document.getElementById('dynamicSeatMap');
    const getAisles = (cols) => {
        if (cols >= 2 && cols <= 6) return [Math.floor(cols / 2)];
        if (cols > 6) return [Math.floor(cols / 3), Math.floor((2 * cols) / 3)];
        return [];
    };
    const aisles = getAisles(avion.cols);

    let html = '<div class="seat-grid">';
    for (let r = 1; r <= avion.rows; r++) {
        let rowClass = null;
        if (avion.first.start > 0 && r >= avion.first.start && r <= avion.first.end) rowClass = 'First';
        else if (avion.biz.start > 0 && r >= avion.biz.start && r <= avion.biz.end) rowClass = 'Business';
        else if (avion.eco.start > 0 && r >= avion.eco.start && r <= avion.eco.end) rowClass = 'Eco';

        if (!rowClass) rowClass = 'Eco';

        html += '<div class="seat-row">';
        html += `<div style="width: 20px; text-align: center; color: var(--flighty-gray); font-weight: bold; font-size: 12px;">${r}</div>`;

        let letterCode = 65; 
        for (let c = 0; c < avion.cols; c++) {
            if (aisles.includes(c)) html += '<div class="seat-aisle"></div>';
            
            const seatLetter = String.fromCharCode(letterCode);
            const seatId = `${r}${seatLetter}`;
            const isTaken = takenSeats.includes(seatId);

            let classes = `seat-cell seat-${rowClass}`;
            if (isTaken) classes += ' taken';

            html += `<div class="${classes}" onclick="selectSeat('${seatId}', this, '${rowClass}')">${seatLetter}</div>`;
            letterCode++;
        }
        html += '</div>';
    }
    html += '</div>';
    container.innerHTML = html;

    window.selectSeat = function(seatId, element, seatClass) {
        if (element.classList.contains('taken')) return;
        if (seatClass !== currentClass) {
            pendingSeat = { id: seatId, el: element, cls: seatClass };
            
            const classRanks = { 'Eco': 1, 'Business': 2, 'First': 3 };
            const isUpgrade = classRanks[seatClass] > classRanks[currentClass];
            
            const header = document.getElementById('classModalHeader');
            const icon = document.getElementById('classModalIcon');
            const confirmBtn = document.getElementById('classModalConfirmBtn');
            const titleText = document.getElementById('classModalTitle');
            
            if (isUpgrade) {
                header.style.backgroundColor = '#1C1C1E';
                icon.className = 'fas fa-arrow-circle-up is-size-1';
                icon.style.color = '#1C1C1E';
                confirmBtn.style.backgroundColor = '#1C1C1E';
                confirmBtn.style.color = '#FFF';
                titleText.innerText = "Surclassement";
                titleText.style.color = '#FFF';
            } else {
                header.style.backgroundColor = '#FFB300';
                icon.className = 'fas fa-arrow-circle-down is-size-1';
                icon.style.color = '#FFB300';
                confirmBtn.style.backgroundColor = '#FFB300';
                confirmBtn.style.color = '#1C1C1E';
                titleText.innerText = "Déclassement";
                titleText.style.color = '#1C1C1E';
            }

            document.getElementById('modalOldClass').innerText = currentClass;
            document.getElementById('modalNewClass').innerText = seatClass;
            document.getElementById('modalNewClass').style.color = isUpgrade ? '#1C1C1E' : '#B27900';
            document.getElementById('modalNewPrice').innerText = prices[seatClass];
            document.getElementById('classChangeModal').classList.add('is-active');
        } else {
            applySeatSelection(seatId, element, seatClass);
        }
    };
    
    window.closeClassModal = function() {
        document.getElementById('classChangeModal').classList.remove('is-active');
        pendingSeat = null;
    };
    
    window.confirmClassChange = function() {
        if (pendingSeat) {
            applySeatSelection(pendingSeat.id, pendingSeat.el, pendingSeat.cls);
            updateInclusFeatures(pendingSeat.cls);
            currentClass = pendingSeat.cls;
        }
        closeClassModal();
    };
    
    function applySeatSelection(seatId, element, seatClass) {
        document.getElementById('input_classe').value = seatClass;
        document.getElementById('input_prix').value = prices[seatClass];
        document.querySelectorAll('.seat-cell').forEach(s => s.classList.remove('selected'));
        element.classList.add('selected');
        document.getElementById('input_seat').value = seatId;
    }
    
    function updateInclusFeatures(cls) {
        const list = document.getElementById('includedFeaturesList');
        if(!list) return;
        
        document.getElementById('inclusTitleClass').innerText = cls;
        if (cls === 'First') {
            list.innerHTML = `<li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> Siège First Class extra-large</li>
                              <li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> 2 Bagages en soute (32kg max)</li>
                              <li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> Repas gastronomique à la carte</li>
                              <li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> Accès aux salons VIP O'Buffair</li>`;
        } else if (cls === 'Business') {
            list.innerHTML = `<li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> Siège Business confortable</li>
                              <li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> 2 Bagages en soute (23kg max)</li>
                              <li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> Menu premium chaud</li>`;
        } else {
            list.innerHTML = `<li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> Siège Economy standard</li>
                              <li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> 1 Bagage cabine (10kg max)</li>
                              <li><i class="fas fa-check-circle mr-2" style="color: var(--success);"></i> Collation standard</li>`;
        }
    }
    
    function handlePopState(event) {
        document.getElementById('leaveWarningModal').classList.add('is-active');
        window.history.pushState({ noBackExitsApp: true }, '');
    }
    
    window.history.pushState({ noBackExitsApp: true }, '');
    window.addEventListener('popstate', handlePopState);

    window.stayOnPage = function() {
        document.getElementById('leaveWarningModal').classList.remove('is-active');
    };

    window.leavePage = function() {
        window.removeEventListener('popstate', handlePopState);
        window.history.go(-2);
    };
    
    document.getElementById('optionsForm').addEventListener('submit', function(e) {
        if (!document.getElementById('input_seat').value) {
            e.preventDefault();
            alert("Veuillez sélectionner un siège sur le plan de la cabine avant de continuer.");
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });
});