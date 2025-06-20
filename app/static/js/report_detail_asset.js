// Asset-Listen Gruppierung - Expandierbare Details

document.addEventListener('DOMContentLoaded', function() {
    // Asset-Listen Daten aus dem Template holen
    const assetList = window.assetList || [];
    
    // Standorte für jede Gruppe aggregieren
    const groupRows = document.querySelectorAll('.group-row');
    groupRows.forEach(row => {
        const name = row.dataset.name;
        const article = row.dataset.article;
        const locationCell = row.querySelector('td:last-child');
        const locations = new Set();
        
        // Alle Assets dieser Gruppe finden und Standorte sammeln
        assetList.forEach(asset => {
            if (asset.item.asset.name === name && 
                (asset.item.asset.article_number === article || 
                (!asset.item.asset.article_number && !article))) {
                if (asset.item.asset.location && asset.item.asset.location.name) {
                    locations.add(asset.item.asset.location.name);
                }
            }
        });
        
        // Standorte in der Zelle anzeigen
        locationCell.innerHTML = Array.from(locations).join(', ') || '-';
    });
    
    // Toggle-Detail Funktion für Gruppen
    const toggleButtons = document.querySelectorAll('.toggle-details');
    toggleButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const row = this.closest('tr');
            const name = row.dataset.name;
            const article = row.dataset.article;
            const detailsRow = document.querySelector(`.details-row[data-parent-name="${name}"][data-parent-article="${article}"]`);
            
            // Toggle Details anzeigen/verstecken
            if (detailsRow.style.display === 'none') {
                detailsRow.style.display = 'table-row';
                this.innerHTML = '<i class="fas fa-minus"></i>';
                
                // Details laden, falls noch nicht erfolgt
                const detailsContainer = detailsRow.querySelector('.details-items');
                if (detailsContainer.children.length === 0) {
                    populateDetails(name, article, detailsContainer);
                }
            } else {
                detailsRow.style.display = 'none';
                this.innerHTML = '<i class="fas fa-plus"></i>';
            }
        });
    });
    
    // Detail-Ansicht Umschalter
    const detailViewToggle = document.getElementById('showDetailedView');
    if (detailViewToggle) {
        detailViewToggle.addEventListener('change', function() {
            const detailRows = document.querySelectorAll('.details-row');
            const toggleBtns = document.querySelectorAll('.toggle-details');
            
            if (this.checked) {
                // Im Detail-Modus alle Details anzeigen
                detailRows.forEach(row => {
                    if (row.style.display === 'none') {
                        const name = row.dataset.parentName;
                        const article = row.dataset.parentArticle;
                        const detailsContainer = row.querySelector('.details-items');
                        
                        row.style.display = 'table-row';
                        
                        // Details laden, falls noch nicht erfolgt
                        if (detailsContainer.children.length === 0) {
                            populateDetails(name, article, detailsContainer);
                        }
                    }
                });
                
                toggleBtns.forEach(btn => btn.innerHTML = '<i class="fas fa-minus"></i>');
            } else {
                // Im Übersichtsmodus alle Details ausblenden
                detailRows.forEach(row => row.style.display = 'none');
                toggleBtns.forEach(btn => btn.innerHTML = '<i class="fas fa-plus"></i>');
            }
        });
    }
    
    // Initialen Zustand auf Basis des Toggles setzen
    if (detailViewToggle && detailViewToggle.checked) {
        const detailRows = document.querySelectorAll('.details-row');
        const toggleBtns = document.querySelectorAll('.toggle-details');
        
        detailRows.forEach(row => {
            const name = row.dataset.parentName;
            const article = row.dataset.parentArticle;
            const detailsContainer = row.querySelector('.details-items');
            
            row.style.display = 'table-row';
            
            if (detailsContainer.children.length === 0) {
                populateDetails(name, article, detailsContainer);
            }
        });
        
        toggleBtns.forEach(btn => btn.innerHTML = '<i class="fas fa-minus"></i>');
    }
});

// Funktion zum Befüllen der Details
function populateDetails(name, article, container) {
    // Passende Assets für diese Gruppe finden
    const assetList = window.assetList || [];
    const assets = assetList.filter(asset => 
        asset.item.asset.name === name && 
        (asset.item.asset.article_number === article || 
        (!asset.item.asset.article_number && !article))
    );
    
    // Für jedes Asset eine Zeile hinzufügen
    assets.forEach(asset => {
        const row = document.createElement('tr');
        
        // Status Badge erstellen
        let statusBadge = '';
        if (asset.dyn_status === 'found') {
            statusBadge = '<span class="badge bg-success">Gefunden</span>';
        } else if (asset.dyn_status === 'missing') {
            statusBadge = '<span class="badge bg-danger">Fehlend</span>';
        } else if (asset.dyn_status === 'damaged') {
            statusBadge = '<span class="badge bg-warning text-dark">Beschädigt</span>';
        } else {
            statusBadge = '<span class="badge bg-secondary">Offen</span>';
        }
        
        // Date formatieren
        const countedDate = asset.item.counted_at ? 
            new Date(asset.item.counted_at).toLocaleDateString('de-DE', { 
                year: 'numeric', 
                month: '2-digit', 
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }) : '-';
        
        // Zellen erstellen
        row.innerHTML = `
            <td>${asset.item.asset.serial_number || '-'}</td>
            <td>${statusBadge}</td>
            <td>${countedDate}</td>
            <td>${asset.item.actual_location || '-'}</td>
            <td>${asset.item.condition || '-'}</td>
        `;
        
        container.appendChild(row);
    });
}
