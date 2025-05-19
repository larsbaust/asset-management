// Checkbox-Logik für Asset-Tabelle

document.addEventListener('DOMContentLoaded', function() {
    // Master-Checkbox steuert alle Zeilen
    const selectAll = document.getElementById('select-all-assets');
    if (selectAll) {
        selectAll.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.asset-checkbox');
            checkboxes.forEach(cb => cb.checked = selectAll.checked);
        });
    }
    // Wenn eine Einzel-Checkbox geändert wird, Master ggf. anpassen
    document.querySelectorAll('.asset-checkbox').forEach(cb => {
        cb.addEventListener('change', function() {
            if (!cb.checked) selectAll.checked = false;
            else if (Array.from(document.querySelectorAll('.asset-checkbox')).every(cb => cb.checked)) selectAll.checked = true;
        });
    });

    // Bulk-Archivieren
    const bulkArchiveBtn = document.getElementById('bulk-archive-btn');
    if (bulkArchiveBtn) {
        bulkArchiveBtn.addEventListener('click', function() {
            const checked = Array.from(document.querySelectorAll('.asset-checkbox:checked'));
            if (checked.length === 0) {
                alert('Bitte mindestens ein Asset auswählen.');
                return;
            }
            if (!confirm('Möchten Sie die ausgewählten Assets wirklich archivieren? Diese Aktion setzt den Status auf "Inaktiv".')) return;
            const ids = checked.map(cb => cb.value);
            fetch('/assets/bulk_archive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) location.reload();
                else alert(data.message || 'Fehler beim Archivieren.');
            })
            .catch(() => alert('Fehler beim Archivieren.'));
        });
    }
});
