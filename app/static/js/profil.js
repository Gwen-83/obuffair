// Logique de navigation des onglets du profil
function switchTab(tabId) {
    // Masquer tous les contenus
    document.querySelectorAll('.content-tab').forEach(t => t.classList.add('is-hidden'));
    // Retirer l'état actif des liens du menu
    document.querySelectorAll('.menu-list a').forEach(a => a.classList.remove('is-active'));
    
    // Afficher le bon contenu
    document.getElementById('tab-' + tabId).classList.remove('is-hidden');
    // Mettre en surbrillance le lien cliqué
    event.currentTarget.classList.add('is-active');
}