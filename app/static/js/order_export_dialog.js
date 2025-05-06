document.addEventListener('DOMContentLoaded', function() {
    console.log('Export-Dialog JS geladen.');
    const previewBtn = document.getElementById('preview-btn');
    if (!previewBtn) return;

    function updatePreview(event) {
        if (event) event.preventDefault();
        const form = previewBtn.closest('form');
        console.log('Gefundenes Form-Element:', form);
        console.log('updatePreview triggered');
        if (!form) return;
        const formData = new FormData(form);
        let params = [];
        for (const [key, value] of formData.entries()) {
            if (key.startsWith('export_')) {
                params.push(`${encodeURIComponent(key)}=1`);
            } else if (key.startsWith('colname_')) {
                params.push(`${encodeURIComponent(key)}=${encodeURIComponent(value)}`);
            }
        }
        params.push('preview=1');
        console.log('Alle Parameter:', params);
        const url = window.location.pathname + '?' + params.join('&');
        console.log('Preview-URL:', url);
        console.log('AJAX wird gesendet!');
        fetch(url)
            .then(resp => resp.json())
            .then(data => {
                const pre = document.getElementById('export-preview-csv');
                let csv = '';
                if (data.header && data.header.length > 0) {
                    csv += data.header.join(';') + '\n';
                }
                if (data.rows && data.rows.length > 0) {
                    for (const row of data.rows) {
                        csv += row.map(cell => (cell !== undefined && cell !== null ? String(cell) : '')).join(';') + '\n';
                    }
                }
                if (data.only_empty) {
                    csv += '\nHinweis: Die gewählten Felder enthalten keine Daten für diese Bestellung.';
                }
                if (!csv.trim()) {
                    csv = 'Keine Daten für Vorschau.';
                }
                pre.textContent = csv;
            });
    }

    previewBtn.addEventListener('click', function(e) { updatePreview(e); });

    // Automatische Aktualisierung bei Änderungen
    const form = previewBtn.closest('form');
    if (form) {
        form.querySelectorAll('input[type="checkbox"][name^="export_"], input[type="text"][name^="colname_"]').forEach(function(input) {
            input.addEventListener('change', updatePreview);
        });
    }

    // Initiale Vorschau
    updatePreview();
});
