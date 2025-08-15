// Chart.js Fill-Fix für Wertentwicklungs-Chart
document.addEventListener('DOMContentLoaded', function() {
  console.log('Chart-Fix für Wertentwicklungs-Chart wird angewendet...');
  
  // Warten, bis Chart.js die Chart gerendert hat
  setTimeout(function() {
    fixValueChartFill();
  }, 1000);
  
  function fixValueChartFill() {
    // Canvas-Element finden
    const valueCanvas = document.getElementById('valueChart');
    if (!valueCanvas) {
      console.error('Wertentwicklungs-Canvas nicht gefunden!');
      return;
    }
    
    // Chart-Instanz holen über Chart.js
    const chartInstance = Chart.getChart(valueCanvas);
    
    if (!chartInstance) {
      console.error('Keine Chart-Instanz für valueChart gefunden!');
      return;
    }
    
    // Debug-Info
    console.log('Wertentwicklungs-Chart gefunden, wende Fix an...');
    
    // Fläche direkt manipulieren
    try {
      // Dataset wählen
      const dataset = chartInstance.data.datasets[0];
      
      // MD3-Farben für die Chart
      // Direkte MD3-Primärfarbe (lila) ohne CSS-Variablen
      const lilaPrimary = '#6750A4'; // Standard MD3 Lila (Primary)
      
      // Direktes Setzen der Farben mit MD3 Lila
      const fillColor = 'rgba(103, 80, 164, 0.2)'; // Lila mit Transparenz
      console.log('Verwende feste MD3-Lila-Farbe für Chart-Füllung:', fillColor);
      
      dataset.backgroundColor = fillColor;
      dataset.fill = {
        target: 'origin',
        above: fillColor
      };
      
      // Auch die Linienfarbe auf sattes MD3-Lila setzen
      dataset.borderColor = lilaPrimary;
      
      // Chart aktualisieren
      chartInstance.update();
      
      // SVG-Elemente für Füllung direkt manipulieren (als Fallback)
      setTimeout(function() {
        const chartArea = valueCanvas.parentNode.querySelector('.chartjs-render-monitor + .chartjs-render-monitor');
        if (chartArea) {
          const paths = chartArea.querySelectorAll('path');
          paths.forEach(path => {
            // Nur Füllungen anpassen (nicht die Linien)
            if (path.getAttribute('stroke') === 'transparent' || !path.getAttribute('stroke')) {
              path.setAttribute('fill', 'rgba(232, 222, 248, 0.5)');
            }
          });
        }
      }, 500);
      
      console.log('Wertentwicklungs-Chart-Fix erfolgreich angewendet!');
    } catch (e) {
      console.error('Fehler beim Anwenden des Chart-Fixes:', e);
    }
  }
});
