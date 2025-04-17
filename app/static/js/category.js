function addNewCategory() {
    document.getElementById('categoryModal').classList.add('is-active');
    document.getElementById('newCategoryName').value = '';
}

function saveNewCategory() {
    const name = document.getElementById('newCategoryName').value;
    if (!name) {
        alert('Bitte einen Namen eingeben.');
        return;
    }
    fetch('/categories/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const select = document.querySelector('select[name="category"]');
            const option = document.createElement('option');
            option.value = data.id;
            option.text = data.name;
            select.appendChild(option);
            select.value = data.id;
            closeModal('categoryModal');
        } else {
            alert(data.message || 'Fehler beim Anlegen der Kategorie.');
        }
    });
}

function confirmDelete(type) {
    if (type !== 'category') return;
    const select = document.querySelector('select[name="category"]');
    const selected = select.options[select.selectedIndex];
    if (!selected || !selected.value) {
        alert('Bitte eine Kategorie auswählen.');
        return;
    }
    if (!confirm('Kategorie wirklich löschen?')) return;
    fetch('/categories/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: selected.text })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            select.removeChild(selected);
            select.selectedIndex = 0;
        } else {
            alert(data.message || 'Fehler beim Löschen der Kategorie.');
        }
    });
}
