// Robustes Live-Update für Fortschritt und Boxen
function updateProgressAndCounts() {
    console.log("updateProgressAndCounts called");
    try {
        const countedInputs = document.querySelectorAll('input[name^="counted_quantity_"]');
        const damagedInputs = document.querySelectorAll('input[name^="damaged_quantity_"]');
        let total = 0;
        let counted = 0;
        let found = 0;
        let damaged = 0;
        let missing = 0;
        let pending = 0;
        // Hole Soll-Mengen pro Zeile
        const sollMengen = Array.from(countedInputs).map(input => {
            const row = input.closest('tr');
            if (!row) return 0;
            const tds = Array.from(row.querySelectorAll('td'));
            const cell = tds[3]; // 4. sichtbare Spalte
            if (!cell) return 0;
            return parseInt(cell.innerText) || 0;
        });
        // Summiere
        countedInputs.forEach((input, idx) => {
            const soll = sollMengen[idx];
            let gez = parseInt(input.value) || 0;
            const defDamaged = damagedInputs[idx] ? (parseInt(damagedInputs[idx].value) || 0) : 0;
            // Begrenze gezählte Menge auf Soll-Menge
            if (gez > soll) gez = soll;
            total += soll;
            counted += gez;
            damaged += defDamaged;
            found += Math.max(gez - defDamaged, 0);
            missing += Math.max(soll - gez, 0);
        });
        pending = Math.max(total - counted, 0);
        // Fortschritt
        let percent = total > 0 ? (Math.min(counted, total) / total * 100) : 0;
        if(document.getElementById('progress-bar')) document.getElementById('progress-bar').value = percent;
        if(document.getElementById('progress-text')) document.getElementById('progress-text').innerText = `Fortschritt: ${counted} von ${total} Mengen erfasst (${percent.toFixed(1)}%)`;
        if(document.getElementById('found-count')) document.getElementById('found-count').innerText = found;
        if(document.getElementById('damaged-count')) document.getElementById('damaged-count').innerText = damaged;
        if(document.getElementById('missing-count')) document.getElementById('missing-count').innerText = missing;
        if(document.getElementById('pending-count')) document.getElementById('pending-count').innerText = pending + ' Stück';
    } catch (e) {
        console.error('Fehler beim Live-Update:', e);
    }
}
window.addEventListener('DOMContentLoaded', function() {
    const inputs = document.querySelectorAll('input[name^="counted_quantity_"], input[name^="damaged_quantity_"]');
    console.log("Gefundene Inputs:", inputs.length, inputs);
    inputs.forEach(input => {
        input.addEventListener('input', function(e) {
            console.log('Input-Event auf', e.target.name, 'neuer Wert:', e.target.value);
            updateProgressAndCounts();
        });
    });
    updateProgressAndCounts(); // Initiales Update bei Seitenaufruf
});
