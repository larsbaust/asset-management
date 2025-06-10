/**
 * Order Calculator - Hilfsfunktionen zur Berechnung von Bestellsummen
 * Für Asset Management System
 * 
 * Created: 09.06.2025
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Order Calculator geladen");
    
    // Gib die Tabellenstruktur aus für Debug-Zwecke
    const tables = document.querySelectorAll('table');
    console.log(`Gefundene Tabellen: ${tables.length}`);
    
    // Stelle sicher, dass der Calculator erst läuft wenn das DOM vollständig geladen ist
    setTimeout(function() {
        console.log("Starte Berechnung nach Timeout...");
        calculateOrderTotal();
    }, 500);
    
    // Funktion zur Neuberechnung des Gesamtwerts
    function calculateOrderTotal() {
        console.log("Berechne Gesamtwert...");
        
        // Finde die Tabelle mit den Artikeln
        const orderTable = document.querySelector('.table.is-fullwidth.is-striped');
        if (!orderTable) {
            console.error("Keine Bestelltabelle gefunden!");
            return;
        }
        console.log("Tabelle gefunden:", orderTable);
        
        // Finde alle normalen Artikel-Zeilen (nicht die Debug-Zeile oder Summenzeile)
        const rows = Array.from(orderTable.querySelectorAll('tbody tr')).filter(row => {
            return !row.classList.contains('has-background-light') && 
                   !row.classList.contains('has-background-warning-light');
        });
        
        console.log(`${rows.length} Artikelzeilen gefunden`);  
        
        let totalValue = 0;
        let totalItems = 0;
        
        // Iteriere über alle Zeilen
        rows.forEach(function(row, index) {
            try {
                // Debug: Zeige alle Zellen dieser Zeile
                const cells = row.querySelectorAll('td');
                console.log(`Zeile ${index+1}: ${cells.length} Zellen`);
                
                // Überspringe die Zeile, wenn sie leer ist oder weniger als 7 Zellen hat
                if (cells.length < 7) {
                    console.log(`Zeile ${index+1} übersprungen: zu wenige Zellen`); 
                    return;
                }
                
                // Extrahiere den Wert (Einzelwert) - 5. Spalte
                const valueCell = cells[4];
                if (!valueCell) {
                    console.log(`Zeile ${index+1}: Keine Wertzelle gefunden`);
                    return;
                }
                
                // Extrahiere die Menge - 6. Spalte
                const quantityCell = cells[5];
                if (!quantityCell) {
                    console.log(`Zeile ${index+1}: Keine Mengenzelle gefunden`);
                    return;
                }
                
                // Extrahiere den Gesamtwert pro Zeile - 7. Spalte
                const totalCell = cells[6];
                if (!totalCell) {
                    console.log(`Zeile ${index+1}: Keine Gesamtwertzelle gefunden`);
                    return;
                }
                
                // Konvertiere die Werte
                const valueText = valueCell.textContent.trim().replace('€', '').replace(',', '.').trim();
                const value = parseFloat(valueText) || 0;
                
                const quantityText = quantityCell.textContent.trim();
                const quantity = parseInt(quantityText) || 1;
                
                // Berechne den Gesamtwert für diese Zeile
                const lineTotal = value * quantity;
                
                console.log(`Zeile ${index+1}: Wert=${value}€, Menge=${quantity}, Berechnet=${lineTotal}€`);
                
                // Aktualisiere die Zelleninhalte, falls nötig
                totalCell.textContent = lineTotal.toLocaleString('de-DE', { 
                    style: 'currency',
                    currency: 'EUR',
                    minimumFractionDigits: 2
                });
                
                // Zu Gesamtwerten hinzufügen
                totalValue += lineTotal;
                totalItems += quantity;
                
                console.log(`Zeile verarbeitet: Wert=${value}€, Menge=${quantity}, Summe=${lineTotal}€`);
            } catch (e) {
                console.error("Fehler bei der Berechnung einer Zeile:", e);
            }
        });
        
        console.log(`Gesamtberechnung: ${totalItems} Artikel, Gesamtwert: ${totalValue}€`);
        
        // Aktualisiere die Gesamtsumme in der Tabelle - letzte Zeile, letzte Zelle
        const totalRows = document.querySelectorAll('tr.has-background-light');
        console.log(`Gefundene Summenzeilen: ${totalRows.length}`);
        
        if (totalRows.length > 0) {
            // Nehme die letzte Summenzeile
            const totalRow = totalRows[totalRows.length - 1];
            console.log("Summenzeile gefunden:", totalRow);
            
            // Finde alle Zellen in der Summenzeile
            const totalCells = totalRow.querySelectorAll('td');
            console.log(`Zellen in der Summenzeile: ${totalCells.length}`);
            
            if (totalCells.length > 0) {
                // Aktualisiere die letzte Zelle (Gesamtwert)
                const totalValueCell = totalCells[totalCells.length - 1];
                if (totalValueCell) {
                    // Formatiere den Wert als Währung
                    totalValueCell.textContent = totalValue.toLocaleString('de-DE', { 
                        style: 'currency', 
                        currency: 'EUR',
                        minimumFractionDigits: 2
                    });
                    console.log("Gesamtwert aktualisiert:", totalValueCell.textContent);
                    
                    // Hebe den aktualisierten Wert optisch hervor
                    totalValueCell.classList.add('has-text-weight-bold');
                    totalValueCell.style.color = '#209cee';
                }
                
                // Aktualisiere die Mengenzelle (vorletzte oder die mit dem Index 5)
                const quantityIndex = totalCells.length > 6 ? 5 : totalCells.length - 2;
                const totalItemsCell = totalCells[quantityIndex];
                if (totalItemsCell) {
                    totalItemsCell.textContent = totalItems;
                    console.log("Gesamtmenge aktualisiert:", totalItemsCell.textContent);
                    totalItemsCell.classList.add('has-text-weight-bold');
                }
            }
        } else {
            console.warn("Keine Summenzeile gefunden - erstelle eine neue");
            
            try {
                // Wenn keine Summenzeile existiert, füge eine hinzu
                const tbody = orderTable.querySelector('tbody');
                if (tbody) {
                    const newRow = document.createElement('tr');
                    newRow.className = 'has-background-light';
                    
                    const cell1 = document.createElement('td');
                    cell1.textContent = 'Gesamt:';
                    cell1.className = 'has-text-weight-bold';
                    
                    const emptyCells = [];
                    for (let i = 0; i < 4; i++) {
                        emptyCells.push(document.createElement('td'));
                    }
                    
                    const quantityCell = document.createElement('td');
                    quantityCell.textContent = totalItems;
                    quantityCell.className = 'has-text-weight-bold';
                    
                    const totalCell = document.createElement('td');
                    totalCell.textContent = totalValue.toLocaleString('de-DE', { 
                        style: 'currency', 
                        currency: 'EUR',
                        minimumFractionDigits: 2
                    });
                    totalCell.className = 'has-text-weight-bold';
                    totalCell.style.color = '#209cee';
                    
                    newRow.appendChild(cell1);
                    emptyCells.forEach(cell => newRow.appendChild(cell));
                    newRow.appendChild(quantityCell);
                    newRow.appendChild(totalCell);
                    
                    tbody.appendChild(newRow);
                    console.log("Neue Summenzeile erstellt und hinzugefügt");
                }
            } catch (e) {
                console.error("Fehler beim Erstellen der Summenzeile:", e);
            }
        }
    }
    
    // Initial berechnen mit Verzögerung um sicherzugehen, dass das DOM bereit ist
    setTimeout(calculateOrderTotal, 200);
    
    // Bei Änderungen der Werte oder Mengen neu berechnen
    document.querySelectorAll('input[type="number"]').forEach(function(input) {
        input.addEventListener('change', calculateOrderTotal);
        input.addEventListener('input', calculateOrderTotal);
    });
    
    // Füge einen Debug-Button hinzu, um die Berechnung manuell auszulösen
    const addDebugButton = function() {
        try {
            const container = document.querySelector('.wizard-container');
            if (!container) return;
            
            const button = document.createElement('button');
            button.className = 'button is-small is-info is-light';
            button.style.marginTop = '10px';
            button.textContent = 'Gesamtberechnung aktualisieren';
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log("Manuelle Neuberechnung angefordert");
                calculateOrderTotal();
            });
            
            container.appendChild(button);
            console.log("Debug-Button hinzugefügt");
        } catch (e) {
            console.error("Fehler beim Hinzufügen des Debug-Buttons:", e);
        }
    };
    
    // Debug-Button hinzufügen
    setTimeout(addDebugButton, 500);
});
