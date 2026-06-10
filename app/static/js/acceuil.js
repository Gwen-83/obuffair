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

    // --- Carte Globale des Routes (Non-Interactive) ---
    const mapRoutesDataEl = document.getElementById('mapRoutesData');
    if (mapRoutesDataEl && document.getElementById('network-map')) {
        const mapRoutes = JSON.parse(mapRoutesDataEl.dataset.routes || '[]');
        
        if (mapRoutes.length > 0) {
            // Initialisation de la carte AVEC interaction (sauf scroll molette)
            const map = L.map('network-map', {
                scrollWheelZoom: false,
                attributionControl: false
            });
            
            // Fond de carte clair et épuré (CartoDB Positron)
            L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                maxZoom: 20
            }).addTo(map);

            const bounds = [];
            const addedPoints = new Set();

            mapRoutes.forEach(route => {
                const startLatLng = [route.dep_lat, route.dep_lng];
                const endLatLng = [route.arr_lat, route.arr_lng];
                
                bounds.push(startLatLng, endLatLng);

                // Générer une ligne géodésique (courbure de la terre) avec Arc.js
                const generator = new arc.GreatCircle(
                    { x: route.dep_lng, y: route.dep_lat },
                    { x: route.arr_lng, y: route.arr_lat }
                );
                const line = generator.Arc(100, { offset: 10 });
                const leafLatLngs = line.geometries[0].coords.map(c => [c[1], c[0]]);

                // Tracer la ligne de vol incurvée (Bleu O'Buffair)
                L.polyline(leafLatLngs, {
                    color: '#002A5C',
                    weight: 2,
                    opacity: 0.4,
                    smoothFactor: 1
                }).addTo(map);

                // Ajouter les aéroports et leurs labels IATA
                [ 
                    { lat: route.dep_lat, lng: route.dep_lng, iata: route.dep_iata },
                    { lat: route.arr_lat, lng: route.arr_lng, iata: route.arr_iata }
                ].forEach(pt => {
                    const key = `${pt.lat},${pt.lng}`;
                    if (!addedPoints.has(key)) {
                        // Point de l'aéroport (Bleu plein avec effet glow)
                        L.circleMarker([pt.lat, pt.lng], { radius: 4, fillColor: '#002A5C', color: '#002A5C', weight: 1, fillOpacity: 1, className: 'airport-glow-point' }).addTo(map);
                        
                        // Étiquette IATA 3D style
                        const icon = L.divIcon({
                            className: 'airport-iata-label',
                            html: `<div>${pt.iata}</div>`,
                            iconSize: [40, 20],
                            iconAnchor: [-8, 10] // Décalé légèrement sur la droite
                        });
                        L.marker([pt.lat, pt.lng], { icon: icon }).addTo(map);

                        addedPoints.add(key);
                    }
                });
            });

            if (bounds.length > 0) {
                setTimeout(() => map.fitBounds(bounds, { padding: [50, 50] }), 100);
            }
        }
    }
});