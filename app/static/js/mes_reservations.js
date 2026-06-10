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
                btn.innerHTML = 'Voir les cartes d\'embarquement <i class="fas fa-chevron-down ml-2"></i>';
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
});