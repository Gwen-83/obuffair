document.addEventListener('DOMContentLoaded', () => {
    // Gestion de l'affichage/masquage des cartes d'embarquement (Détails)
    const toggleButtons = document.querySelectorAll('.toggle-details-btn');
    
    toggleButtons.forEach(btn => {
        // Initialisation de l'accessibilité (A11y)
        const targetId = btn.getAttribute('data-target');
        btn.setAttribute('aria-expanded', 'false');
        btn.setAttribute('aria-controls', targetId);

        btn.addEventListener('click', () => {
            const targetWrapper = document.getElementById(targetId);
            
            if (targetWrapper.classList.contains('is-active')) {
                targetWrapper.classList.remove('is-active');
                btn.innerHTML = 'Voir les détails <i class="fas fa-chevron-down ml-2"></i>';
                btn.classList.remove('is-active');
                btn.setAttribute('aria-expanded', 'false');
            } else {
                targetWrapper.classList.add('is-active');
                btn.innerHTML = 'Masquer les détails <i class="fas fa-chevron-up ml-2"></i>';
                btn.classList.add('is-active');
                btn.setAttribute('aria-expanded', 'true');
            }
        });
    });

    // Ouverture automatique de l'onglet si un hash est présent dans l'URL (ex: #details-1)
    if (window.location.hash && window.location.hash.startsWith('#details-')) {
        const targetId = window.location.hash.substring(1);
        const targetBtn = document.querySelector(`.toggle-details-btn[data-target="${targetId}"]`);
        
        if (targetBtn) {
            targetBtn.click(); // Simule un clic pour ouvrir l'onglet
            setTimeout(() => {
                targetBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300); // Léger délai pour laisser l'onglet s'ouvrir avant de scroller
        }
    }
});