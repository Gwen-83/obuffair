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
});