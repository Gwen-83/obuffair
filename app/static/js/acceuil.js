// app/static/js/acceuil.js

document.addEventListener("DOMContentLoaded", () => {
    // --- Animation Carrousel d'Images ---
    const carousel = document.getElementById("destinationsCarousel");
    if (carousel) {
        // Cloner les éléments du carrousel pour créer une boucle ininterrompue
        const items = [...carousel.children];
        items.forEach(item => {
            carousel.appendChild(item.cloneNode(true));
        });

        let scrollInterval;
        const autoScroll = () => {
            // Si on a défilé la moitié (la copie), on réinitialise discrètement au début
            if (carousel.scrollLeft >= carousel.scrollWidth / 2) {
                carousel.scrollLeft = 0;
            }
            carousel.scrollLeft += 1; // Fait avancer le défilement vers la droite (les cartes glissent vers la gauche)
        };
        
        scrollInterval = setInterval(autoScroll, 30);
        
        // Met en pause quand on survole une image avec la souris
        carousel.addEventListener('mouseenter', () => clearInterval(scrollInterval));
        carousel.addEventListener('mouseleave', () => scrollInterval = setInterval(autoScroll, 30));
    }

    // --- Animation Texte Départ / Arrivée via DB ---
    const airportsDataEl = document.getElementById('airportsData');
    if (airportsDataEl) {
        const airports = JSON.parse(airportsDataEl.dataset.airports || '[]');
        if (airports.length >= 2) {
            const departText = document.getElementById('anim-depart-text');
            const arriveeText = document.getElementById('anim-arrivee-text');
            
            // Initialisation aléatoire
            let depIdx = Math.floor(Math.random() * airports.length);
            let arrIdx = (depIdx + 1) % airports.length; // S'assurer que arr != dep
            
            departText.innerText = `${airports[depIdx].city} (${airports[depIdx].iata})`;
            arriveeText.innerText = `${airports[arrIdx].city} (${airports[arrIdx].iata})`;

            setInterval(() => {
                // 1. Fade out
                departText.classList.add('fade-out');
                arriveeText.classList.add('fade-out');
                
                setTimeout(() => {
                    // 2. Changer le texte (Départ et arrivée distincts)
                    depIdx = (depIdx + 1) % airports.length;
                    arrIdx = (depIdx + Math.floor(Math.random() * (airports.length - 1)) + 1) % airports.length;
                    
                    departText.innerText = `${airports[depIdx].city} (${airports[depIdx].iata})`;
                    arriveeText.innerText = `${airports[arrIdx].city} (${airports[arrIdx].iata})`;
                    
                    // 3. Préparer et déclencher le fade-in
                    departText.classList.remove('fade-out');
                    arriveeText.classList.remove('fade-out');
                    departText.classList.add('fade-in');
                    arriveeText.classList.add('fade-in');
                    
                    setTimeout(() => {
                        departText.classList.remove('fade-in');
                        arriveeText.classList.remove('fade-in');
                    }, 50);
                }, 400); // Temps correspondant à la durée de la transition CSS (0.4s)
            }, 3500); // Rotation toutes les 3.5 secondes
        }
    }

    // --- Carte Globale des Routes (Interactive) ---
    const mapRoutesDataEl = document.getElementById('mapRoutesData');
    if (mapRoutesDataEl && document.getElementById('network-map')) {
        const mapRoutes = JSON.parse(mapRoutesDataEl.dataset.routes || '[]');
        
        if (mapRoutes.length > 0) {
            // Initialisation de la carte
            const map = L.map('network-map', {
                scrollWheelZoom: false,
                attributionControl: false
            });
            
            // Créer un "pane" (calque) dédié pour les labels, pour s'assurer qu'ils ne bloquent pas les clics
            map.createPane('labels');
            map.getPane('labels').style.zIndex = 650;

            // Fond de carte clair et épuré (CartoDB Positron)
            L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                maxZoom: 20
            }).addTo(map);

            // Extraire la liste unique des aéroports depuis les routes
            const airportsMap = new Map();
            mapRoutes.forEach(r => {
                if (!airportsMap.has(r.dep_iata)) airportsMap.set(r.dep_iata, { iata: r.dep_iata, lat: r.dep_lat, lng: r.dep_lng });
                if (!airportsMap.has(r.arr_iata)) airportsMap.set(r.arr_iata, { iata: r.arr_iata, lat: r.arr_lat, lng: r.arr_lng });
            });
            const airports = Array.from(airportsMap.values());
            const allBounds = L.latLngBounds(airports.map(pt => [pt.lat, pt.lng]));

            const routesLayerGroup = L.layerGroup().addTo(map);
            const airportsLayerGroup = L.layerGroup().addTo(map);

            let currentMode = 'hub'; // Mode par défaut
            let selectedHub = null;
            let isTransitioning = false; // Sécurité pour éviter le spam click

            const btnModeHub = document.getElementById('btn-mode-hub');
            const btnModeAll = document.getElementById('btn-mode-all');
            const mapHint = document.getElementById('map-interaction-hint');

            function drawMap() {
                isTransitioning = true;
                routesLayerGroup.clearLayers();
                airportsLayerGroup.clearLayers();

                const drawnRoutes = [];
                
                // Choix des vols à tracer
                if (currentMode === 'all') {
                    drawnRoutes.push(...mapRoutes);
                    if (mapHint) mapHint.style.opacity = '0';
                } else {
                    if (mapHint) mapHint.style.opacity = '1';
                    if (selectedHub) {
                        drawnRoutes.push(...mapRoutes.filter(r => r.dep_iata === selectedHub || r.arr_iata === selectedHub));
                        if (mapHint) mapHint.innerHTML = `<i class="fas fa-info-circle mr-1"></i> Vols directs depuis/vers <span style="color: var(--primary);">${selectedHub}</span>. Cliquez ailleurs pour réinitialiser.`;
                    } else {
                        if (mapHint) mapHint.innerHTML = `<i class="fas fa-hand-pointer mr-1"></i> Cliquez sur un aéroport pour voir ses vols directs.`;
                    }
                }

                // Dessin des routes sélectionnées
                drawnRoutes.forEach(route => {
                    const generator = new arc.GreatCircle(
                        { x: route.dep_lng, y: route.dep_lat },
                        { x: route.arr_lng, y: route.arr_lat }
                    );
                    const line = generator.Arc(100, { offset: 10 });
                    const leafLatLngs = line.geometries[0].coords.map(c => [c[1], c[0]]);

                    L.polyline(leafLatLngs, {
                        color: '#002A5C',
                        weight: currentMode === 'hub' ? 2 : 1.5,
                        opacity: currentMode === 'hub' ? 0.5 : 0.3,
                        smoothFactor: 1
                    }).addTo(routesLayerGroup);
                });

                // Dessin des aéroports (Noeuds)
                airports.forEach(pt => {
                    const isSelectedHub = (currentMode === 'hub' && selectedHub === pt.iata);
                    const isConnected = drawnRoutes.some(r => r.dep_iata === pt.iata || r.arr_iata === pt.iata);
                    const isFaded = currentMode === 'hub' && selectedHub && !isSelectedHub && !isConnected;

                    const fillColor = isSelectedHub ? 'var(--accent)' : '#002A5C';
                    const opacity = isFaded ? 0.2 : 1;
                    const radius = isSelectedHub ? 7 : (isConnected && currentMode === 'hub' ? 5 : 4);

                    const circle = L.circleMarker([pt.lat, pt.lng], {
                        radius: radius,
                        fillColor: fillColor,
                        color: isSelectedHub ? '#fff' : fillColor,
                        weight: isSelectedHub ? 2 : 1,
                        fillOpacity: opacity,
                        opacity: opacity,
                        className: 'airport-glow-point' + (isSelectedHub ? ' active-hub' : '') + (currentMode === 'hub' ? ' clickable' : '')
                    });

                    const onNodeClick = (e) => {
                        L.DomEvent.stopPropagation(e);
                        if (isTransitioning) return;
                        selectedHub = (selectedHub === pt.iata) ? null : pt.iata; // Toggle
                        drawMap();
                    };

                    if (currentMode === 'hub') {
                        circle.bindTooltip(`Voir les vols - ${pt.iata}`, { direction: 'top', className: 'hub-tooltip' });
                        circle.on('click', onNodeClick);
                    }

                    circle.addTo(airportsLayerGroup);

                    // Labels textuels
                    if (!isFaded || isSelectedHub) {
                        const icon = L.divIcon({
                            className: 'airport-iata-label' + (currentMode === 'hub' ? ' clickable' : ''),
                            html: `<div style="opacity: ${opacity}; ${isSelectedHub ? 'border-color: var(--accent); background: white;' : ''}">${pt.iata}</div>`,
                            iconSize: [40, 20],
                            iconAnchor: [-8, 10]
                        });
                        const labelMarker = L.marker([pt.lat, pt.lng], { icon: icon, interactive: currentMode === 'hub', pane: 'labels' }).addTo(airportsLayerGroup);
                        if (currentMode === 'hub') {
                            labelMarker.on('click', onNodeClick);
                        }
                    }
                });

                // Ajustement dynamique de la caméra (Auto-Zoom)
                if (currentMode === 'hub' && selectedHub) {
                    const activePoints = airports.filter(pt => pt.iata === selectedHub || drawnRoutes.some(r => r.dep_iata === pt.iata || r.arr_iata === pt.iata));
                    if (activePoints.length > 0) {
                        map.flyToBounds(L.latLngBounds(activePoints.map(p => [p.lat, p.lng])), { padding: [50, 50], duration: 0.8 });
                    }
                } else if (airports.length > 0) {
                    map.flyToBounds(allBounds, { padding: [50, 50], duration: 0.8 });
                }

                isTransitioning = false;
            }

            // Désélection du hub lors d'un clic dans le vide sur la carte
            map.on('click', () => {
                if (currentMode === 'hub' && selectedHub && !isTransitioning) {
                    selectedHub = null;
                    drawMap();
                }
            });
                        
            // Gestionnaires de clics pour les boutons
            if (btnModeHub && btnModeAll) {
                btnModeHub.addEventListener('click', () => {
                    if (currentMode === 'hub' || isTransitioning) return;
                    currentMode = 'hub';
                    btnModeHub.classList.replace('is-light', 'is-primary');
                    btnModeHub.classList.add('is-selected');
                    btnModeAll.classList.replace('is-primary', 'is-light');
                    btnModeAll.classList.remove('is-selected');
                    drawMap();
                });

                btnModeAll.addEventListener('click', () => {
                    if (currentMode === 'all' || isTransitioning) return;
                    currentMode = 'all';
                    selectedHub = null;
                    btnModeAll.classList.replace('is-light', 'is-primary');
                    btnModeAll.classList.add('is-selected');
                    btnModeHub.classList.replace('is-primary', 'is-light');
                    btnModeHub.classList.remove('is-selected');
                    drawMap();
                });
            }

            // Ajuster la caméra initiale
            const initBounds = airports.map(pt => [pt.lat, pt.lng]);
            if (initBounds.length > 0) {
                map.fitBounds(initBounds, { padding: [50, 50] });
            }

            // Premier rendu
            drawMap();
        }
    }
});