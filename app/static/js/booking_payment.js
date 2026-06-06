document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('paymentForm');
    const overlay = document.getElementById('payment-overlay');
    const payButton = document.getElementById('payButton');
    
    if (form && overlay) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            overlay.classList.add('is-active');
            
            // Double protection : désactiver le bouton pour éviter les clics multiples
            if (payButton) {
                payButton.disabled = true;
                payButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Traitement...';
            }
            
            // Simule un délai de traitement de paiement pour l'UX
            setTimeout(() => { form.submit(); }, 2500);
        });
    }
});