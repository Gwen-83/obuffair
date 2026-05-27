// app/static/js/profil.js
// Extrait depuis profil.html pour séparer le JS de l'HTML

// JS simple pour changer d'onglet
function switchTab(tabId) {
    document.querySelectorAll('.content-tab').forEach(t => t.classList.add('is-hidden'));
    document.querySelectorAll('.menu-list a').forEach(a => a.classList.remove('is-active'));
    document.getElementById('tab-' + tabId).classList.remove('is-hidden');
    
    // Utilisation de l'event global si disponible (pour inline onclick)
    if (window.event && window.event.currentTarget) {
        window.event.currentTarget.classList.add('is-active');
    }
}