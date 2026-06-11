// --- FIX CACHE NAVIGATEUR (Bouton Retour) ---
window.addEventListener('pageshow', function(event) {
    if (event.persisted) {
        window.location.reload();
    }
});

document.addEventListener("DOMContentLoaded", () => {
    const flightDataElement = document.getElementById('bookingFlightsData');
    if (!flightDataElement) return;

    const MAX_PASSENGERS = parseInt(flightDataElement.dataset.maxPassengers || 1);
    const multiSelections = {};

    window.updateMultiClass = function(flightId, seatClass, delta, price, maxAvail = 999) {
        if (!multiSelections[flightId]) {
            multiSelections[flightId] = { counts: { 'Eco': 0, 'Business': 0, 'First': 0 }, totalCount: 0, totalPrice: 0 };
        }
        const data = multiSelections[flightId];
        
        if (delta > 0) {
            if (data.totalCount >= MAX_PASSENGERS) return;
            if (data.counts[seatClass] >= maxAvail) return;
            data.counts[seatClass]++;
            data.totalCount++;
            data.totalPrice += price;
        } else if (delta < 0) {
            if (data.counts[seatClass] <= 0) return;
            data.counts[seatClass]--;
            data.totalCount--;
            data.totalPrice -= price;
        }
        
        // Met à jour l'interface (compteurs et prix)
        document.getElementById(`count-${flightId}-${seatClass}`).innerText = data.counts[seatClass];
        document.getElementById(`total-count-${flightId}`).innerText = data.totalCount;
        document.getElementById(`total-price-${flightId}`).innerText = data.totalPrice.toFixed(2);
        
        // Injecte la liste correcte de inputs "classes[]" en fonction des quantités
        const container = document.getElementById(`hidden-classes-container-${flightId}`);
        container.innerHTML = '';
        for (const [cls, count] of Object.entries(data.counts)) {
            for (let i = 0; i < count; i++) {
                container.innerHTML += `<input type="hidden" name="classes[]" value="${cls}">`;
            }
        }
        
        // Le prix moyen qui sera passé au backend (calcul final : * nb_passagers)
        document.getElementById(`prix-${flightId}`).value = data.totalCount > 0 ? (data.totalPrice / MAX_PASSENGERS).toFixed(2) : 0;
        
        // Le bouton valider n'est cliquable que si tous les passagers ont été affectés à une classe
        document.getElementById(`btn-submit-${flightId}`).disabled = (data.totalCount !== MAX_PASSENGERS);
        
        // Verrouillage visuel : Griser les autres vols
        let activeFlightId = null;
        for (const fId of Object.keys(multiSelections)) {
            if (multiSelections[fId].totalCount > 0) {
                activeFlightId = fId;
                break;
            }
        }
        
        document.querySelectorAll('.flighty-booking-card').forEach(card => {
            if (!card.id || !card.id.startsWith('flight-card-')) return;
            const cardFlightId = card.id.replace('flight-card-', '');
            
            if (activeFlightId && cardFlightId !== activeFlightId) {
                card.style.opacity = '0.4';
                card.style.pointerEvents = 'none';
            } else {
                card.style.opacity = '1';
                card.style.pointerEvents = 'auto';
            }
        });
    };

    // --- RESTAURATION DE LA SÉLECTION PRÉCÉDENTE (Multi-Passagers) ---
    const selectedFlightId = flightDataElement.dataset.selectedFlight;
    if (selectedFlightId && selectedFlightId !== 'None' && MAX_PASSENGERS > 1) {
        const card = document.getElementById(`flight-card-${selectedFlightId}`);
        if (card) {
            const form = card.querySelector('form');
            if (form) {
                const priceEco = parseFloat(form.querySelector('input[name="prix_eco"]').value);
                const priceBiz = parseFloat(form.querySelector('input[name="prix_biz"]').value);
                const priceFirst = parseFloat(form.querySelector('input[name="prix_first"]').value);
                const selectedClasses = JSON.parse(flightDataElement.dataset.selectedClasses || '[]');
                
                selectedClasses.forEach(cls => {
                    let price = cls === 'Eco' ? priceEco : (cls === 'Business' ? priceBiz : priceFirst);
                    window.updateMultiClass(selectedFlightId, cls, 1, price, 999);
                });
            }
        }
    }

    // --- ANIMATION DE SURBRILLANCE (Etape des classes) ---
    if (flightDataElement && flightDataElement.dataset.highlight) {
        const parts = flightDataElement.dataset.highlight.split('_');
        if (parts[0] === 'classe') {
            const tariffs = document.querySelector('.flight-tariffs-section');
            if (tariffs) {
                tariffs.scrollIntoView({ behavior: 'smooth', block: 'center' });
                tariffs.style.transition = 'all 0.5s ease';
                tariffs.style.boxShadow = '0 0 0 4px var(--accent)';
                tariffs.style.borderRadius = '16px';
                setTimeout(() => { tariffs.style.boxShadow = 'none'; }, 2000);
            }
        }
    }
});

let currentPassengerNum = 1;
let currentLegType = 'aller';
let currentLegIdx = 0;
let pendingSeatAction = null;
let passengers = [];
let basePricesAller = {};
let basePricesRetour = {};
let isModification = false;
let originalTotal = 0;

/**
 * Met à jour l'affichage du modèle de l'avion pour le segment de vol sélectionné.
 * @param {string} type - 'aller' ou 'retour'
 * @param {number} idx - L'index du segment de vol
 */
function updateAircraftModelDisplay(type, idx) {
    const mapContainer = document.getElementById(`map-${type}-${idx}`);
    const aircraftModelDisplay = document.getElementById('aircraft-model-display');
    if (aircraftModelDisplay && mapContainer && mapContainer.dataset.avion) {
        const avion = JSON.parse(mapContainer.dataset.avion);
        aircraftModelDisplay.innerHTML = `<span class="has-text-weight-normal">${avion.modele}</span> - `;
    } else if (aircraftModelDisplay) {
        aircraftModelDisplay.innerHTML = ''; // Vide le champ si aucune donnée
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const dataEl = document.getElementById('bookingOptionsData');
    if (!dataEl) return;


    passengers = JSON.parse(dataEl.dataset.passengers || '[]');
    passengers.forEach(p => {
        p.originalClasseAller = p.classe_aller;
        p.originalClasseRetour = p.classe_retour;
    });
    basePricesAller = JSON.parse(dataEl.dataset.basePricesAller || '{}');
    basePricesRetour = JSON.parse(dataEl.dataset.basePricesRetour || '{}');
    currentLegType = dataEl.dataset.currentLegType || 'aller';
    isModification = dataEl.dataset.isModification === 'true';
    originalTotal = parseFloat(dataEl.dataset.originalTotal || '0');

    window.buildAllMaps();
    window.updateAllPassengerCards();
    window.selectPassenger(1);
    window.updatePassengerBadges();
    window.checkAllSeatsAssigned();

    // Appel initial pour afficher le modèle du premier avion
    updateAircraftModelDisplay(currentLegType, 0);

    // --- ANIMATION DE SURBRILLANCE (Etape des options) ---
    if (dataEl && dataEl.dataset.highlight) {
        const parts = dataEl.dataset.highlight.split('_');
        if (parts.length >= 2) {
            const optionType = parts[0];
            const pIndex = parseInt(parts[1]);
            const pNum = pIndex + 1;
            
            if (typeof window.selectPassenger === 'function') {
                window.selectPassenger(pNum);
            }
            
            setTimeout(() => {
                let elToHighlight = null;
                if (optionType === 'siege') {
                    elToHighlight = document.getElementById(`pass-seat-badge-${pIndex}`);
                } else if (optionType === 'bagage') {
                    const lbl = document.getElementById(`bagage_label_${pNum}`);
                    if (lbl) elToHighlight = lbl.parentElement;
                } else if (optionType === 'repas') {
                    const sel = document.getElementById(`repas_select_${pNum}`);
                    if (sel) elToHighlight = sel.parentElement;
                }
                if (elToHighlight) {
                    elToHighlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    elToHighlight.style.transition = 'all 0.5s ease';
                    elToHighlight.style.boxShadow = '0 0 0 4px var(--accent)';
                    elToHighlight.style.borderRadius = '8px';
                    setTimeout(() => { elToHighlight.style.boxShadow = 'none'; }, 2000);
                }
            }, 500);
        }
    }
});

window.updateAllPassengerCards = function() {
    passengers.forEach(p => {
        const cls = currentLegType === 'aller' ? p.classe_aller : p.classe_retour;
        const el = document.getElementById(`pass-class-${p.index}`);
        if(el) el.innerText = cls;
        window.updatePassengerOptions(p.index);
    });
}

window.selectPassenger = function(num, preventScroll = false) {
    currentPassengerNum = num;
    document.querySelectorAll('.passenger-option-card').forEach(c => {
        c.classList.remove('is-active');
    });
    
    const card = document.getElementById('pass-card-' + (num-1));
    if(card) {
        card.classList.add('is-active');
        if(!preventScroll) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    updateSeatMapVisuals();

    if(!preventScroll) {
        const pIndex = passengers.findIndex(p => p.num === num);
        if(pIndex !== -1) {
            const pass = passengers[pIndex];
            const container = document.getElementById(`map-${currentLegType}-${currentLegIdx}`);
            if(container) {
                let targetRow = 1;
                const avionStr = container.dataset.avion;
                const passCls = currentLegType === 'aller' ? pass.classe_aller : pass.classe_retour;
                if(avionStr) {
                    const avion = JSON.parse(avionStr);
                    if (passCls === 'First' && avion.first_rang_de > 0) targetRow = avion.first_rang_de;
                    else if (passCls === 'Business' && avion.bus_rang_de > 0) targetRow = avion.bus_rang_de;
                    else if (passCls === 'Eco' && avion.eco_rang_de > 0) targetRow = avion.eco_rang_de;
                }
                const row = document.getElementById(`seat-row-${currentLegType}-${currentLegIdx}-${targetRow}`);
                if(row) {
                    const topPos = row.offsetTop - container.offsetTop - 20;
                    container.scrollTo({ top: Math.max(0, topPos), behavior: 'smooth' });
                }
            }
        }
    }
}

window.switchLeg = function(type, idx, element) {
    currentLegType = type;
    currentLegIdx = idx;
    document.querySelectorAll('.segment-item').forEach(t => t.classList.remove('is-active'));
    if(element) element.classList.add('is-active');

    document.querySelectorAll('.seat-map-container').forEach(c => c.style.display = 'none');
    document.getElementById('map-' + type + '-' + idx).style.display = 'block';
    
    // Met à jour l'affichage du modèle d'avion lors du changement de segment
    updateAircraftModelDisplay(type, idx);
    window.updateAllPassengerCards();
    window.updatePassengerBadges();
    
    let nextToSelect = 1;
    for(let i = 0; i < passengers.length; i++) {
        const inp = document.getElementById(`siege_${type}_${idx}_${passengers[i].num}`);
        if(inp && !inp.value) { nextToSelect = passengers[i].num; break; }
    }
    selectPassenger(nextToSelect, false);
}

window.buildAllMaps = function() {
    const getAisles = (cols) => {
        if (cols >= 2 && cols <= 6) return [Math.floor(cols / 2)];
        if (cols > 6) return [Math.floor(cols / 3), Math.floor((2 * cols) / 3)];
        return [];
    };

    document.querySelectorAll('.seat-map-container').forEach(container => {
        const avion = JSON.parse(container.dataset.avion);
        const taken = JSON.parse(container.dataset.taken);
        const type = container.dataset.type;
        const idx = container.dataset.idx;

        let html = '<div class="seat-grid">';
        
        if (!avion || avion.nb_rangees === 0) {
            html += '<div class="notification is-warning has-text-centered mt-5" style="border-radius: 12px;">Le plan de cabine n\'est pas disponible pour ce vol. L\'assignation de siège se fera à l\'enregistrement.</div></div>';
            container.innerHTML = html;
            return;
        }

        const aisles = getAisles(avion.largeur_rangee);
        let previousRowClass = null;

        for(let r = 1; r <= avion.nb_rangees; r++) {
            let seatClass = 'Eco';
            if (avion.first_rang_de > 0 && r >= avion.first_rang_de && r <= avion.first_rang_a) seatClass = 'First';
            else if (avion.bus_rang_de > 0 && r >= avion.bus_rang_de && r <= avion.bus_rang_a) seatClass = 'Business';
            else if (avion.eco_rang_de > 0 && r >= avion.eco_rang_de && r <= avion.eco_rang_a) seatClass = 'Eco';

            if (previousRowClass && previousRowClass !== seatClass) {
                html += `<div class="class-divider"><span>Cabine ${seatClass}</span></div>`;
            } else if (r === 1) {
                html += `<div class="class-divider" style="border: none; margin: 0 0 12px 0;"><span style="top: 0;">Cabine ${seatClass}</span></div>`;
            }
            previousRowClass = seatClass;

            html += `<div class="seat-row" id="seat-row-${type}-${idx}-${r}">`;
            html += `<div style="width: 20px; text-align: center; color: var(--flighty-gray); font-weight: bold; font-size: 12px;">${r}</div>`;

            let letterCode = 65; // Démarre à 'A'
            for(let c = 0; c < avion.largeur_rangee; c++) {
                if(aisles.includes(c)) html += `<div class="seat-aisle"></div>`;
                
                const seatLetter = String.fromCharCode(letterCode);
                const seatId = `${r}${seatLetter}`;
                const isTaken = taken.includes(seatId);
                
                const display = isTaken ? '<i class="fas fa-times" style="font-size:0.7rem; color:var(--flighty-gray);"></i>' : seatLetter;
                html += `<div class="seat-cell seat-${seatClass} ${isTaken ? 'taken' : ''}" data-seat="${seatId}" 
                              onclick="seatClicked('${type}', ${idx}, '${seatId}', '${seatClass}', ${isTaken})">${display}</div>`;
                letterCode++;
            }
            html += `</div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    });
}

function getRank(cls) {
    if(cls === 'First') return 3;
    if(cls === 'Business') return 2;
    return 1;
}

function getHighestClass(p) {
    const r1 = getRank(p.classe_aller);
    const r2 = p.classe_retour ? getRank(p.classe_retour) : 0;
    const max = Math.max(r1, r2);
    if (max === 3) return 'First';
    if (max === 2) return 'Business';
    return 'Eco';
}

window.seatClicked = function(type, idx, seatId, seatClass, isTaken) {
    if(isTaken) return;
    const passIndex = passengers.findIndex(p => p.num === currentPassengerNum);
    const pass = passengers[passIndex];
    
    let alreadySelectedBy = null;
    passengers.forEach(p => {
        const input = document.getElementById(`siege_${type}_${idx}_${p.num}`);
        if(input && input.value === seatId && p.num !== currentPassengerNum) { alreadySelectedBy = p.num; }
    });
    if(alreadySelectedBy) {
        alert("Ce siège est déjà sélectionné par le passager P" + alreadySelectedBy); return;
    }

    const currentInput = document.getElementById(`siege_${type}_${idx}_${pass.num}`);
    if(currentInput && currentInput.value === seatId) {
        currentInput.value = '';
        updateSeatMapVisuals(); updatePassengerBadges(); checkAllSeatsAssigned(); return;
    }

    const currentClass = type === 'aller' ? pass.classe_aller : pass.classe_retour;
    if(currentClass !== seatClass) {
        pendingSeatAction = { type, idx, seatId, seatClass, passIndex };
        const isUpgrade = getRank(seatClass) > getRank(currentClass);
        const prices = type === 'aller' ? basePricesAller : basePricesRetour;
        const originalClass = type === 'aller' ? pass.originalClasseAller : pass.originalClasseRetour;
        const diff = (prices[seatClass] || 0) - (prices[originalClass] || 0);

        const header = document.getElementById('classModalHeader');
        const icon = document.getElementById('classModalIcon');
        const confirmBtn = document.getElementById('classModalConfirmBtn');
        const titleText = document.getElementById('classModalTitle');
        
        if (isUpgrade) {
            header.style.backgroundColor = '#1C1C1E'; icon.className = 'fas fa-arrow-circle-up is-size-1'; icon.style.color = '#1C1C1E';
            confirmBtn.style.backgroundColor = '#1C1C1E'; confirmBtn.style.color = '#FFF'; titleText.innerText = "Surclassement"; titleText.style.color = '#FFF';
        } else {
            header.style.backgroundColor = '#FFB300'; icon.className = 'fas fa-arrow-circle-down is-size-1'; icon.style.color = '#FFB300';
            confirmBtn.style.backgroundColor = '#FFB300'; confirmBtn.style.color = '#1C1C1E'; titleText.innerText = "Déclassement"; titleText.style.color = '#1C1C1E';
        }
        
        document.getElementById('modalOldClass').innerText = currentClass;
        document.getElementById('modalNewClass').innerText = seatClass;
        document.getElementById('modalNewClass').style.color = isUpgrade ? '#1C1C1E' : '#B27900';
        document.getElementById('modalNewPrice').innerText = diff > 0 ? `+ ${diff.toFixed(2)} €` : `${diff.toFixed(2)} €`;
        document.getElementById('classChangeModal').classList.add('is-active');
    } else {
        applySeatSelection(type, idx, seatId, seatClass, passIndex);
    }
}

window.closeClassModal = function() {
    document.getElementById('classChangeModal').classList.remove('is-active');
    pendingSeatAction = null;
}

window.confirmClassChange = function() {
    if(pendingSeatAction) {
        applySeatSelection(pendingSeatAction.type, pendingSeatAction.idx, pendingSeatAction.seatId, pendingSeatAction.seatClass, pendingSeatAction.passIndex);
    }
    closeClassModal();
}

function applySeatSelection(type, idx, seatId, seatClass, passIndex) {
    const pass = passengers[passIndex];
    document.getElementById(`siege_${type}_${idx}_${pass.num}`).value = seatId;
    
    const currentClass = type === 'aller' ? pass.classe_aller : pass.classe_retour;
    if (currentClass !== seatClass) {
        if (type === 'aller') {
            pass.classe_aller = seatClass;
            document.getElementById(`input_classe_aller_${pass.num}`).value = seatClass;
        } else {
            pass.classe_retour = seatClass;
            document.getElementById(`input_classe_retour_${pass.num}`).value = seatClass;
        }
        document.getElementById(`pass-class-${pass.index}`).innerText = seatClass;
        window.updatePassengerOptions(pass.index);
    }
    
    updateSeatMapVisuals();
    updatePassengerBadges();
    checkAllSeatsAssigned();
    calculateGrandTotal();
    
    let nextToSelect = -1;
    for(let i = 0; i < passengers.length; i++) {
        const inp = document.getElementById(`siege_${type}_${idx}_${passengers[i].num}`);
        if(inp && !inp.value) { nextToSelect = passengers[i].num; break; }
    }
    
    if(nextToSelect !== -1) {
        selectPassenger(nextToSelect, false);
    } else {
        selectPassenger(pass.num, true);
        // Tous les sièges de ce vol sont assignés, basculement auto vers le prochain vol
        const segmentItems = Array.from(document.querySelectorAll('.segment-item'));
        const activeTabIdx = segmentItems.findIndex(el => el.classList.contains('is-active'));
        if (activeTabIdx !== -1 && activeTabIdx < segmentItems.length - 1) {
            setTimeout(() => {
                const currentActive = document.querySelector('.segment-item.is-active');
                if (currentActive === segmentItems[activeTabIdx]) {
                    segmentItems[activeTabIdx + 1].click();
                }
            }, 600); // Léger délai (600ms) pour le feedback visuel
        }
    }
}

window.updateSeatMapVisuals = function() {
    document.querySelectorAll('.seat-map-container').forEach(container => {
        const type = container.dataset.type;
        const idx = container.dataset.idx;
        
        container.querySelectorAll('.seat-cell').forEach(cell => {
            cell.classList.remove('selected', 'glowing');
            if(!cell.classList.contains('taken')) {
                const match = cell.dataset.seat.match(/[A-Z]+$/);
                if(match) cell.innerHTML = match[0];
            }
        });
        
        passengers.forEach(p => {
            const input = document.getElementById(`siege_${type}_${idx}_${p.num}`);
            if(input && input.value) {
                const seatCell = container.querySelector(`.seat-cell[data-seat="${input.value}"]`);
                if(seatCell) {
                    seatCell.classList.add('selected');
                    seatCell.innerHTML = `P${p.num}`;
                    if(p.num === currentPassengerNum) { seatCell.classList.add('glowing'); }
                }
            }
        });
    });
}

window.updatePassengerOptions = function(pIndex) {
    const p = passengers[pIndex];
    const highestClass = getHighestClass(p);
    const pNum = passengers[pIndex].num;
    const bagLabel = document.getElementById(`bagage_label_${pNum}`);
    const bagControls = document.getElementById(`bagage_controls_${pNum}`);
    const repasSelect = document.getElementById(`repas_select_${pNum}`);
    const tarifs = JSON.parse(document.getElementById('optionsForm').dataset.tarifs || '{}');
    
    if (highestClass === 'First' || highestClass === 'Business') {
        bagLabel.innerHTML = `<i class="fas fa-suitcase-rolling mr-2 option-icon"></i> Sup. (+${tarifs.bagages_eco['1'] || 45}€/bag) <br><small class="has-text-grey" style="font-weight: 500;">(Déjà 2x${highestClass === 'First' ? '32kg' : '23kg'} Inclus)</small>`;
        bagControls.style.setProperty('display', 'flex', 'important');
        repasSelect.innerHTML = `<option value="${highestClass === 'First' ? 'gastronomique' : 'premium'}">Menu ${highestClass === 'First' ? 'Gastronomique' : 'Premium'} (Inclus)</option><option value="vegetarien">Menu Végétarien (Inclus)</option>`;
    } else {
        bagLabel.innerHTML = `<i class="fas fa-suitcase-rolling mr-2 option-icon"></i> Bagage 23kg (+${tarifs.bagages_eco['1'] || 45}€)`;
        bagControls.style.setProperty('display', 'flex', 'important');
        repasSelect.innerHTML = `<option value="standard">Standard (Inclus)</option><option value="premium">Premium (+${tarifs.repas_eco['premium'] || 15}€)</option><option value="vegetarien">Végétarien (+${tarifs.repas_eco['vegetarien'] || 15}€)</option>`;
    }
    
    const initRepas = document.getElementById(`init_repas_${pNum}`);
    if (initRepas && !p.initializedOptions) {
        if (repasSelect.querySelector(`option[value="${initRepas.value}"]`)) {
            repasSelect.value = initRepas.value;
        }
        p.initializedOptions = true;
    }
    
    const bagInput = document.getElementById(`input_bagages_${pNum}`);
    if (bagInput) {
        document.getElementById(`bagages_count_${pNum}`).innerText = bagInput.value;
    }
    
    // Mise à jour du total si changement de repas
    if (repasSelect) {
        repasSelect.onchange = window.calculateGrandTotal;
    }
}

window.updatePassengerBadges = function() {
    passengers.forEach(p => {
        const inputCurrentLeg = document.getElementById(`siege_${currentLegType}_${currentLegIdx}_${p.num}`);
        
        const badge = document.getElementById(`pass-seat-badge-${p.index}`);
        const cls = currentLegType === 'aller' ? p.classe_aller : p.classe_retour;
        if(inputCurrentLeg && inputCurrentLeg.value) {
            badge.className = "tag is-success is-glowing is-medium font-weight-bold";
            badge.innerHTML = `<i class="fas fa-check mr-2"></i> ${cls} (${inputCurrentLeg.value})`;
        } else {
            badge.className = "tag is-light is-medium font-weight-bold";
            badge.innerHTML = `${cls} • À assigner`;
        }
        
        // Met à jour la classe du thème de la carte selon le segment actif
        const card = document.getElementById(`pass-card-${p.index}`);
        if (card) {
            card.classList.remove('theme-Eco', 'theme-Business', 'theme-First');
            card.classList.add(`theme-${cls}`);
        }
    });
}

window.checkAllSeatsAssigned = function() {
    let allAssigned = true;
    let missing = 0;
    // Sélectionner dynamiquement tous les champs de sièges via leur préfixe d'ID
    document.querySelectorAll('input[id^="siege_"]').forEach(inp => { if(!inp.value) { allAssigned = false; missing++; }});
    
    const remainingDisplay = document.getElementById('remaining-seats-display');
    if (remainingDisplay) {
        if (missing === 0) {
            remainingDisplay.innerHTML = `<strong style="color: #34C759;"><i class="fas fa-check-circle mr-1"></i> Tous les sièges sont assignés</strong>`;
        } else {
            remainingDisplay.innerHTML = `Il vous reste <strong style="color: var(--primary);">${missing} siège${missing > 1 ? 's' : ''}</strong> à assigner.`;
        }
    }
    
    const btn = document.getElementById('btnSubmitPayment');
    if(btn) {
        if(allAssigned) {
            btn.disabled = false; btn.innerHTML = 'Procéder au Paiement <i class="fas fa-arrow-right ml-2"></i>'; btn.classList.add('btn-glow');
        } else {
            btn.disabled = true; btn.innerHTML = `Vous avez encore ${missing} siège${missing > 1 ? 's' : ''} à assigner`; btn.classList.remove('btn-glow');
        }
    }
}

window.updateBagages = function(num, delta) {
    const span = document.getElementById('bagages_count_' + num);
    const input = document.getElementById('input_bagages_' + num);
    let val = parseInt(span.innerText) + delta;
    if(val < 0) val = 0; if(val > 3) val = 3;
    span.innerText = val; input.value = val;
    calculateGrandTotal();
}

window.calculateGrandTotal = function() {
    let total = 0;
    const tarifs = JSON.parse(document.getElementById('optionsForm').dataset.tarifs || '{}');
    passengers.forEach(p => {
        total += (basePricesAller[p.classe_aller] || 0);
        if (Object.keys(basePricesRetour).length > 0 && p.classe_retour) {
            total += (basePricesRetour[p.classe_retour] || 0);
        }
        
        const highest = getHighestClass(p);
        const bags = document.getElementById('input_bagages_' + p.num).value || '0';
        total += tarifs.bagages_eco[bags] || 0;
        
        if (highest === 'Eco') {
            const repSelect = document.getElementById(`repas_select_${p.num}`);
            if (repSelect) {
                const rep = repSelect.value;
                total += tarifs.repas_eco[rep] || 0;
            }
        }
    });
    
    let totalStr = total.toFixed(2) + ' €';
    const displayEl = document.getElementById('grand_total_display');
    
    if (isModification) {
        const warningEl = document.getElementById('modificationWarning');
        if (total < originalTotal) {
            if (warningEl) warningEl.style.display = 'block';
            if (displayEl) displayEl.innerHTML = `<span style="text-decoration: line-through; color: var(--flighty-gray); font-size: 1.2rem;" class="mr-2">${totalStr}</span>0.00 €`;
            totalStr = '0.00 €';
        } else {
            if (warningEl) warningEl.style.display = 'none';
            const diff = total - originalTotal;
            if (displayEl) displayEl.innerHTML = `<span class="is-size-5 mr-2" style="color: var(--flighty-gray);">+</span>${diff.toFixed(2)} €`;
            totalStr = '+' + diff.toFixed(2) + ' €';
        }
    } else {
        if (displayEl) displayEl.innerText = totalStr;
    }
    
    // Synchroniser dynamiquement avec l'en-tête de réservation (Booking Header)
    document.querySelectorAll('.header-total-price, #headerTotalPrice, .panier-total, .booking-base-total, #bookingBaseTotal, #total-panier, .cart-total-price').forEach(el => {
        el.innerHTML = totalStr;
    });
}