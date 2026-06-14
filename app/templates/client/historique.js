document.addEventListener('DOMContentLoaded', () => {
    // Gestion de l'affichage/masquage des détails de l'historique
    const toggleButtons = document.querySelectorAll('.toggle-details-btn-hist');
    
    toggleButtons.forEach(btn => {
        const targetId = btn.getAttribute('data-target');
        btn.setAttribute('aria-expanded', 'false');
        btn.setAttribute('aria-controls', targetId);

        btn.addEventListener('click', () => {
            const targetWrapper = document.getElementById(targetId);
            
            if (targetWrapper.classList.contains('is-active')) {
                targetWrapper.classList.remove('is-active');
                targetWrapper.style.display = 'none';
                btn.innerHTML = 'Voir les détails <i class="fas fa-chevron-down ml-2"></i>';
                btn.classList.remove('is-active');
                btn.setAttribute('aria-expanded', 'false');
            } else {
                targetWrapper.classList.add('is-active');
                targetWrapper.style.display = 'block';
                btn.innerHTML = 'Masquer les détails <i class="fas fa-chevron-up ml-2"></i>';
                btn.classList.add('is-active');
                btn.setAttribute('aria-expanded', 'true');
            }
        });
    });
});