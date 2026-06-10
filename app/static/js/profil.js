// Logique de navigation des onglets du profil
function switchTab(tabId) {
    // Masquer tous les contenus
    document.querySelectorAll('.content-tab').forEach(t => t.classList.add('is-hidden'));
    // Retirer l'état actif des liens du menu
    document.querySelectorAll('.menu-list a[data-tab]').forEach(a => a.classList.remove('is-active'));
    
    // Afficher le bon contenu
    const targetContent = document.getElementById('tab-' + tabId);
    if (targetContent) {
        targetContent.classList.remove('is-hidden');
    }
    // Mettre en surbrillance le lien correspondant
    const targetLink = document.querySelector(`.menu-list a[data-tab="${tabId}"]`);
    if (targetLink) {
        targetLink.classList.add('is-active');
    }
    // Sauvegarder l'onglet actif en mémoire locale
    sessionStorage.setItem('activeProfilTab', tabId);
}

// Mise à jour dynamique du nom de fichier lors d'un upload
document.addEventListener('DOMContentLoaded', () => {
    // Initialiser les écouteurs de navigation pour les onglets
    document.querySelectorAll('.menu-list a[data-tab]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            switchTab(link.getAttribute('data-tab'));
        });
    });

    // Restaurer l'onglet actif après un rechargement (ex: après avoir enregistré)
    const savedTab = sessionStorage.getItem('activeProfilTab');
    if (savedTab) {
        switchTab(savedTab);
    }

    // Gérer dynamiquement tous les champs d'upload (actuels et futurs)
    const fileInputs = document.querySelectorAll('.file-input');
    fileInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const fileNameSpan = e.target.closest('.file-label').querySelector('.file-name');
            const row = e.target.closest('.columns');
            
            // Si on ajoute un fichier, on annule la suppression éventuelle
            if (row) {
                const deleteInput = row.querySelector('input[type="hidden"]');
                if (deleteInput) deleteInput.value = '0';
            }

            if (e.target.files.length > 0) {
                fileNameSpan.textContent = e.target.files[0].name;
                fileNameSpan.classList.add('has-document');
            } else {
                fileNameSpan.textContent = 'Aucun fichier sélectionné';
                fileNameSpan.classList.remove('has-document');
            }
        });
    });

    // Bouton Ajouter un document
    const btnAddDocument = document.getElementById('btnAddDocument');
    const btnAddWrapper = document.getElementById('btnAddDocumentWrapper');
    const row1 = document.getElementById('document-row-1');
    const row2 = document.getElementById('document-row-2');
    const deleteDoc1 = document.getElementById('delete_doc_1');
    const deleteDoc2 = document.getElementById('delete_doc_2');
    
    if (btnAddDocument) {
        btnAddDocument.addEventListener('click', () => {
            if (row1 && (row1.style.display === 'none' || row1.classList.contains('is-hidden'))) {
                row1.style.display = 'flex';
                row1.classList.remove('is-hidden');
                if (deleteDoc1) deleteDoc1.value = '0';
            } else if (row2 && (row2.style.display === 'none' || row2.classList.contains('is-hidden'))) {
                row2.style.display = 'flex';
                row2.classList.remove('is-hidden');
                if (deleteDoc2) deleteDoc2.value = '0';
            }
            
            if (row1 && row2 && 
                (row1.style.display !== 'none' && !row1.classList.contains('is-hidden')) && 
                (row2.style.display !== 'none' && !row2.classList.contains('is-hidden'))) {
                if (btnAddWrapper) {
                    btnAddWrapper.style.display = 'none';
                    btnAddWrapper.classList.add('is-hidden');
                }
            }
        });
    }

    document.querySelectorAll('.btn-delete-doc').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const target = e.currentTarget.getAttribute('data-target');
            const row = document.getElementById('document-row-' + target);
            const deleteInput = document.getElementById('delete_doc_' + target);
            
            if (row) {
                row.style.display = 'none';
                row.classList.add('is-hidden');
                const fileInput = row.querySelector('.file-input');
                const fileNameSpan = row.querySelector('.file-name');
                if (fileInput) fileInput.value = '';
                if (fileNameSpan) {
                    fileNameSpan.textContent = 'Aucun fichier sélectionné';
                    fileNameSpan.classList.remove('has-document');
                }
            }
            if (deleteInput) deleteInput.value = '1';
            if (btnAddWrapper) btnAddWrapper.style.display = 'block';
            if (btnAddWrapper) btnAddWrapper.classList.remove('is-hidden');
        });
    });
});