document.addEventListener('DOMContentLoaded', () => {
    const paymentForm = document.getElementById('paymentForm');
    const paymentOverlay = document.getElementById('payment-overlay');
    const payButton = document.getElementById('payButton');
    const textEl = document.getElementById('planes-loading-text');
    
    const messages = [
        "Dusty chauffe son moteur agricole...",
        "El Chupacabra charme votre banquier...",
        "Skipper valide la tour de contrôle...",
        "Esquive d'un nuage de frais bancaires...",
        "Atterrissage sur le compte en cours..."
    ];
    let msgIndex = 0;

    if (paymentForm && paymentOverlay) {
        paymentForm.addEventListener('submit', function(event) {
            // 1. On vérifie que tous les champs obligatoires (required, maxlength...) sont valides
            if (paymentForm.checkValidity()) {
                
                // Empêche l'envoi immédiat pour laisser le navigateur dessiner l'animation
                event.preventDefault();
                
                // 2. Affichage de l'overlay de chargement
                paymentOverlay.style.display = 'flex';
                paymentOverlay.setAttribute('aria-hidden', 'false');
                
                // 3. Désactivation du bouton pour empêcher le double-clic (Double réservation)
                if (payButton) {
                    payButton.disabled = true;
                    payButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Traitement en cours...';
                }
                
                // 4. Animation des messages rigolos
                if (textEl) {
                    setInterval(() => {
                        msgIndex = (msgIndex + 1) % messages.length;
                        textEl.innerText = messages[msgIndex];
                    }, 2000);
                }
                
                // 5. Envoi effectif du formulaire au serveur immédiatement.
                // L'overlay animera la transition naturellement pendant le chargement réseau.
                paymentForm.submit();
                
            }
            // Si le formulaire est invalide, le navigateur gère les alertes lui-même et l'overlay reste caché.
        });
    }
});