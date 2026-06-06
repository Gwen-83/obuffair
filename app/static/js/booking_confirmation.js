document.addEventListener('DOMContentLoaded', function() {
    // Effet confetti pour célébrer la réservation
    if (typeof confetti === 'function') {
        setTimeout(() => {
            confetti({ particleCount: 150, spread: 90, origin: { y: 0.6 } });
        }, 300);
    }
});