document.addEventListener('DOMContentLoaded', () => {
    const paymentForm = document.getElementById('paymentForm');
    const paymentOverlay = document.getElementById('payment-overlay');
    const payButton = document.getElementById('payButton');
    const textEl = document.getElementById('planes-loading-text');
    const iconContainer = document.getElementById('loader-icon-container');
    const progressBar = document.getElementById('progress-bar-fill');
    const planeProgress = document.getElementById('plane-progress-indicator');
    
    const steps = [
        {
            text: "Enregistrement de la carte bancaire...",
            icon: '<i class="fas fa-money-check-alt"></i>',
            progress: 15
        },
        {
            text: "Passage à la douane de sécurité (3D Secure)...",
            icon: '<i class="fas fa-shield-alt"></i>',
            progress: 40
        },
        {
            text: "Vérification des fonds à la tour de contrôle...",
            icon: '<i class="fas fa-broadcast-tower"></i>',
            progress: 65
        },
        {
            text: "Chargement des menus O'Buffet...",
            icon: '<i class="fas fa-hamburger"></i>',
            progress: 85
        },
        {
            text: "Paiement autorisé ! Décollage imminent ✈️",
            icon: '<i class="fas fa-plane-departure"></i>',
            progress: 100
        }
    ];
    let stepIndex = 0;

    if (paymentForm && paymentOverlay) {
        paymentForm.addEventListener('submit', function(event) {
            if (paymentForm.checkValidity()) {
                
                event.preventDefault();
                
                paymentOverlay.style.display = 'flex';
                paymentOverlay.setAttribute('aria-hidden', 'false');
                
                if (payButton) {
                    payButton.disabled = true;
                    payButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Traitement en cours...';
                }
                
                stepIndex = 0;
                updateStep();
                
                const interval = setInterval(() => {
                    stepIndex++;
                    if (stepIndex < steps.length) {
                        updateStep();
                    } else {
                        clearInterval(interval);
                        paymentForm.submit();
                    }
                }, 1500); // Reste 1.5s par étape (7.5s au total pour simuler la sécurité et créer l'attente)
            }
        });
    }

    function updateStep() {
        if (!textEl || !iconContainer || !progressBar || !planeProgress) return;
        
        const step = steps[stepIndex];
        
        textEl.style.opacity = '0';
        iconContainer.style.opacity = '0';
        iconContainer.style.transform = 'scale(0.5)';
        
        setTimeout(() => {
            textEl.innerText = step.text;
            iconContainer.innerHTML = step.icon;
            
            textEl.style.transition = 'opacity 0.3s ease';
            iconContainer.style.transition = 'opacity 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
            
            textEl.style.opacity = '1';
            iconContainer.style.opacity = '1';
            iconContainer.style.transform = 'scale(1)';
        }, 300);
        
        progressBar.style.width = step.progress + '%';
        planeProgress.style.left = step.progress + '%';
    }
});