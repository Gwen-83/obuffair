// app/static/js/acceuil.js
// Ce fichier est désormais vide car la page d'accueil utilise uniquement 
// des animations CSS pour la recherche, et le processus de réservation a été déplacé.

document.addEventListener("DOMContentLoaded", () => {
    const carousel = document.getElementById("destinationsCarousel");
    if (carousel) {
        let scrollInterval;
        const autoScroll = () => {
            if (carousel.scrollWidth - carousel.clientWidth <= carousel.scrollLeft + 1) {
                carousel.scrollTo({ left: 0, behavior: 'smooth' }); // Reviens au début en douceur
            } else {
                carousel.scrollLeft += 1;
            }
        };
        
        scrollInterval = setInterval(autoScroll, 30);
        
        // Met en pause quand on survole une image avec la souris
        carousel.addEventListener('mouseenter', () => clearInterval(scrollInterval));
        carousel.addEventListener('mouseleave', () => scrollInterval = setInterval(autoScroll, 30));
    }
});