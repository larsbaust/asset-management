// Dashboard Charts - Initialisierung für Chart.js mit Material Design 3 Styling
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM geladen, initialisiere Dashboard Charts mit MD3 Styling...');
  initializeDashboardCharts();
});

// Hauptfunktion zur Chart-Initialisierung
function initializeDashboardCharts() {
  console.log('Starte Dashboard Chart Initialisierung mit MD3 Design...');
  
  // Funktion zum Auslesen von CSS-Variablen
  function getCssVariable(varName) {
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  }

  function hexToRgbString(hex) {
    if (!hex) {
      return '';
    }
    let normalized = hex.replace('#', '').trim();
    if (normalized.length === 3) {
      normalized = normalized.split('').map(char => char + char).join('');
    }
    if (normalized.length !== 6) {
      return '';
    }
    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    if ([r, g, b].some(Number.isNaN)) {
      return '';
    }
    return `${r}, ${g}, ${b}`;
  }
  
  // MD3-Farbsystem für Charts initialisieren
  const md3Colors = {
    // Primärfarben
    primary: getCssVariable('--md-sys-color-primary'),
    onPrimary: getCssVariable('--md-sys-color-on-primary'),
    primaryContainer: getCssVariable('--md-sys-color-primary-container'),
    onPrimaryContainer: getCssVariable('--md-sys-color-on-primary-container'),
    
    // Sekundärfarben
    secondary: getCssVariable('--md-sys-color-secondary'),
    onSecondary: getCssVariable('--md-sys-color-on-secondary'),
    secondaryContainer: getCssVariable('--md-sys-color-secondary-container'),
    onSecondaryContainer: getCssVariable('--md-sys-color-on-secondary-container'),
    
    // Tertiärfarben
    tertiary: getCssVariable('--md-sys-color-tertiary'),
    onTertiary: getCssVariable('--md-sys-color-on-tertiary'),
    tertiaryContainer: getCssVariable('--md-sys-color-tertiary-container'),
    onTertiaryContainer: getCssVariable('--md-sys-color-on-tertiary-container'),
    
    // Fehlerfarben
    error: getCssVariable('--md-sys-color-error'),
    onError: getCssVariable('--md-sys-color-on-error'),
    errorContainer: getCssVariable('--md-sys-color-error-container'),
    onErrorContainer: getCssVariable('--md-sys-color-on-error-container'),
    
    // Oberflächenfarben
    background: getCssVariable('--md-sys-color-background'),
    onBackground: getCssVariable('--md-sys-color-on-background'),
    surface: getCssVariable('--md-sys-color-surface'),
    onSurface: getCssVariable('--md-sys-color-on-surface'),
    surfaceVariant: getCssVariable('--md-sys-color-surface-variant'),
    onSurfaceVariant: getCssVariable('--md-sys-color-on-surface-variant'),
    
    // Umrissfarben
    outline: getCssVariable('--md-sys-color-outline'),
    outlineVariant: getCssVariable('--md-sys-color-outline-variant'),
    
    // Schattenfarbe
    shadow: getCssVariable('--md-sys-color-shadow'),
    
    // Container-Farben
    surfaceContainerLowest: getCssVariable('--md-sys-color-surface-container-lowest'),
    surfaceContainerLow: getCssVariable('--md-sys-color-surface-container-low'),
    surfaceContainer: getCssVariable('--md-sys-color-surface-container'),
    surfaceContainerHigh: getCssVariable('--md-sys-color-surface-container-high'),
    surfaceContainerHighest: getCssVariable('--md-sys-color-surface-container-highest')
  };
  
  // RGB-Werte für transparente Varianten extrahieren
  const primaryRGB = getCssVariable('--md-sys-color-primary-rgb') || hexToRgbString(md3Colors.primary);
  const secondaryRGB = getCssVariable('--md-sys-color-secondary-rgb') || hexToRgbString(md3Colors.secondary);
  const tertiaryRGB = getCssVariable('--md-sys-color-tertiary-rgb') || hexToRgbString(md3Colors.tertiary);
  const surfaceRGB = getCssVariable('--md-sys-color-surface-rgb') || hexToRgbString(md3Colors.surface);
  
  // Transparente Farbvarianten für Charts
  md3Colors.primaryAlpha = primaryRGB ? `rgba(${primaryRGB}, 0.2)` : `${md3Colors.primary}33`;
  md3Colors.secondaryAlpha = secondaryRGB ? `rgba(${secondaryRGB}, 0.2)` : `${md3Colors.secondary}33`;
  md3Colors.tertiaryAlpha = tertiaryRGB ? `rgba(${tertiaryRGB}, 0.2)` : `${md3Colors.tertiary}33`;
  md3Colors.surfaceAlpha = surfaceRGB ? `rgba(${surfaceRGB}, 0.8)` : `${md3Colors.surface}CC`;
  
  // Chart-Farbpalette mit mehr Farben für Charts mit vielen Segmenten
  md3Colors.chartPalette = [
    md3Colors.primary,
    md3Colors.secondary,
    md3Colors.tertiary,
    md3Colors.error,
    md3Colors.primaryContainer,
    md3Colors.secondaryContainer,
    md3Colors.tertiaryContainer,
    getCssVariable('--md-ref-palette-primary50'),
    getCssVariable('--md-ref-palette-secondary50'),
    getCssVariable('--md-ref-palette-tertiary50'),
    getCssVariable('--md-ref-palette-neutral80'),
    getCssVariable('--md-ref-palette-neutral70'),
    getCssVariable('--md-ref-palette-neutral-variant60'),
    getCssVariable('--md-ref-palette-neutral-variant70')
  ];
  
  // Eine Hilfsfunktion, um sicherzustellen, dass wir immer eine gültige Farbe haben
  md3Colors.getChartColor = function(index) {
    // Modulo-Operation, damit wir nie out-of-bounds gehen
    const safeIndex = index % md3Colors.chartPalette.length;
    return md3Colors.chartPalette[safeIndex] || '#6750A4'; // Fallback zur primären MD3-Farbe
  };
  
  console.log('MD3 Farben geladen:', md3Colors.primary, md3Colors.secondary, md3Colors.tertiary);
  
  // MD3 Typography System
  const md3Typography = {
    titleLarge: {
      family: getCssVariable('--md-sys-typescale-title-large-font-family'),
      size: getCssVariable('--md-sys-typescale-title-large-font-size'),
      weight: getCssVariable('--md-sys-typescale-title-large-font-weight'),
      lineHeight: getCssVariable('--md-sys-typescale-title-large-line-height')
    },
    titleMedium: {
      family: getCssVariable('--md-sys-typescale-title-medium-font-family'),
      size: getCssVariable('--md-sys-typescale-title-medium-font-size'),
      weight: getCssVariable('--md-sys-typescale-title-medium-font-weight'),
      lineHeight: getCssVariable('--md-sys-typescale-title-medium-line-height')
    },
    labelLarge: {
      family: getCssVariable('--md-sys-typescale-label-large-font-family'),
      size: getCssVariable('--md-sys-typescale-label-large-font-size'),
      weight: getCssVariable('--md-sys-typescale-label-large-font-weight'),
      lineHeight: getCssVariable('--md-sys-typescale-label-large-line-height')
    },
    labelMedium: {
      family: getCssVariable('--md-sys-typescale-label-medium-font-family'),
      size: getCssVariable('--md-sys-typescale-label-medium-font-size'),
      weight: getCssVariable('--md-sys-typescale-label-medium-font-weight'),
      lineHeight: getCssVariable('--md-sys-typescale-label-medium-line-height')
    },
    bodyMedium: {
      family: getCssVariable('--md-sys-typescale-body-medium-font-family'),
      size: getCssVariable('--md-sys-typescale-body-medium-font-size'),
      weight: getCssVariable('--md-sys-typescale-body-medium-font-weight'),
      lineHeight: getCssVariable('--md-sys-typescale-body-medium-line-height')
    },
    bodySmall: {
      family: getCssVariable('--md-sys-typescale-body-small-font-family'),
      size: getCssVariable('--md-sys-typescale-body-small-font-size'),
      weight: getCssVariable('--md-sys-typescale-body-small-font-weight'),
      lineHeight: getCssVariable('--md-sys-typescale-body-small-line-height')
    }
  };
  
  // MD3 Spacing und Shape
  const md3 = {
    colors: md3Colors,
    typography: md3Typography,
    
    // Spacing und Layout aus Material Design 3
    spacing: {
      xs: '4px',
      sm: '8px',
      md: '16px',
      lg: '24px',
      xl: '32px'
    },
    
    // Schatten und Elevation
    elevation: {
      level1: '0px 1px 2px rgba(0,0,0,0.3), 0px 1px 3px 1px rgba(0,0,0,0.15)',
      level2: '0px 1px 2px rgba(0,0,0,0.3), 0px 2px 6px 2px rgba(0,0,0,0.15)',
      level3: '0px 4px 8px 3px rgba(0,0,0,0.15), 0px 1px 3px rgba(0,0,0,0.3)'
    },
    
    // Shape System aus Material Design 3
    shape: {
      corner: {
        xs: '4px',
        sm: '8px',
        md: '12px', 
        lg: '16px',
        xl: '28px',
        full: '50%'
      }
    }
  };
  
  // Chart.js Standardeinstellungen mit MD3 Design
  Chart.defaults.font.family = md3.typography.bodyMedium.family;
  Chart.defaults.color = md3Colors.onSurfaceVariant;
  Chart.defaults.scale.grid.color = md3Colors.outlineVariant;
  Chart.defaults.scale.ticks.color = md3Colors.onSurfaceVariant;
  
  // Globales Plugin für MD3-Styling
  Chart.register({
    id: 'md3Styling',
    beforeDraw: function(chart) {
      // Hintergrund für Charts, falls gewünscht
      if (chart.config.options.md3Background) {
        const ctx = chart.ctx;
        ctx.save();
        ctx.fillStyle = md3.colors.surfaceContainerHigh || 'var(--md-sys-color-surface-container-high)';
        ctx.fillRect(0, 0, chart.width, chart.height);
        ctx.restore();
      }
    }
  });
  
  // Angepasste MD3 Plugin für erweiterte Tooltips
  const md3TooltipPlugin = {
    id: 'md3Tooltip',
    beforeTooltipDraw: function(chart, args, options) {
      const { tooltip } = args;
      const ctx = chart.ctx;
      
      if (tooltip && tooltip.opacity > 0) {
        // MD3 Schatten für Tooltips
        ctx.shadowColor = 'rgba(0, 0, 0, 0.2)';
        ctx.shadowBlur = 8;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 2;
      }
    }
  };
  
  // MD3 Animations-Plugin mit sanften Übergängen
  const md3AnimationPlugin = {
    id: 'md3Animation',
    beforeInit: function(chart) {
      if (chart.config.type === 'doughnut' || chart.config.type === 'pie') {
        chart.options.animation = {
          animateRotate: true,
          animateScale: true,
          duration: 600,
          easing: 'easeOutQuart'
        };
      } else if (chart.config.type === 'line') {
        chart.options.animation = {
          duration: 800,
          easing: 'easeOutCubic'
        };
      }
    }
  };
  
  // Registriere die Plugins
  // Tooltip-Plugin deaktiviert, um Konflikte mit Chart.js Hover-Events zu vermeiden
  // Chart.register(md3TooltipPlugin);
  Chart.register(md3AnimationPlugin);
  
  // 1. Kostenverteilungs-Chart initialisieren
  initCostDistributionChart();
  
  // 2. Wertentwicklung-Chart initialisieren
  initValueDevelopmentChart();
  
  // 3. Assets nach Kategorie und Zuordnung Chart initialisieren
  // initCategoryAssignmentChart(); // Deaktiviert - wird jetzt in dashboard.html gehandhabt
  
  // Kostenverteilungs-Chart laden
  function initCostDistributionChart() {
    console.log('Initialisiere Kostenverteilung Chart mit MD3 Design...');
    const costCanvas = document.getElementById('costChart');
    if (!costCanvas) {
      console.error('FEHLER: Kostenverteilung Canvas #costChart nicht gefunden!');
      return;
    }
    
    const container = document.getElementById('cost-chart-container');
    if (container) {
      // Sanfte Überblendung während des Ladens
      container.style.transition = 'opacity 0.3s ease-in-out';
      container.style.opacity = '0.6';
    }
    
    // Daten vom Backend laden
    fetch('/api/dashboard/cost-distribution')
      .then(response => {
        if (!response.ok) {
          throw new Error(`Netzwerkantwort nicht OK: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // Prüfen ob die API leere Daten zurückgibt
        if (!data?.cost_distribution?.labels?.length) {
          throw new Error('Keine Daten vorhanden');
        }
        return data;
      })
      .catch(error => {
        console.warn('Fallback zu Test-Daten:', error);
        // Fallback zu lokalen Testdaten
        try {
          const fallbackElement = document.getElementById('cost-chart-fallback-data');
          if (fallbackElement) {
            return JSON.parse(fallbackElement.textContent);
          } else {
            throw new Error('Fallback-Element nicht gefunden');
          }
        } catch (e) {
          console.error('Fehler beim Laden der Fallback-Daten:', e);
          return null; // Keine Fallback-Daten mehr
        }
      })
      .then(data => {
        // Wenn keine Daten vorhanden, Chart ausblenden
        if (!data || !data.cost_distribution || !data.cost_distribution.labels || data.cost_distribution.labels.length === 0) {
          console.log('Keine Kostenverteilungs-Daten - Chart wird ausgeblendet');
          if (costCanvas) {
            costCanvas.style.display = 'none';
          }
          if (container) {
            container.style.display = 'none';
          }
          return;
        }
        
        if (container) {
          container.style.opacity = '1'; // Zeige den Chart-Container
        }
        
        // MD3 Palette für Donut Chart
        const palette = md3.colors.chartPalette;
        
        // Chart-Konfiguration mit MD3 Styling
        new Chart(costCanvas, {
          type: 'doughnut',
          data: {
            labels: data.cost_distribution.labels,
            datasets: [{
              data: data.cost_distribution.data,
              backgroundColor: function(context) {
                return md3Colors.getChartColor(context.dataIndex);
              },
              borderColor: md3Colors.surfaceContainer,
              borderWidth: 1,
              borderRadius: 4,
              spacing: 2,
              hoverOffset: 0
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            md3Background: false,
            interaction: {
              mode: 'nearest',
              intersect: true
            },
            layout: {
              padding: {
                top: parseInt(md3.spacing.sm) || 8,
                right: parseInt(md3.spacing.sm) || 8,
                bottom: parseInt(md3.spacing.sm) || 8,
                left: parseInt(md3.spacing.sm) || 8
              }
            },
            plugins: {
              legend: {
                position: 'bottom',
                align: 'center',
                labels: {
                  padding: parseInt(md3.spacing.md) || 16,
                  usePointStyle: true,
                  pointStyle: 'rectRounded',
                  boxWidth: 10,
                  boxHeight: 10,
                  font: {
                    family: md3.typography.labelMedium.family,
                    size: parseInt(md3.typography.labelMedium.size) || 14,
                    weight: md3.typography.labelMedium.weight || 500
                  }
                }
              },
              tooltip: {
                enabled: true,
                callbacks: {
                  label: function(context) {
                    const label = context.label || '';
                    const value = context.raw || 0;
                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                    const percentage = total ? Math.round((value / total) * 100) : 0;
                    const formatter = new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' });
                    return `${label}: ${formatter.format(value)} (${percentage}%)`;
                  }
                }
              }
            }
          }
        });
        
        console.log('Kostenverteilungs-Chart mit MD3 Design erfolgreich geladen');
      });
  }
  
  // Wertentwicklung-Chart laden
  function initValueDevelopmentChart() {
    console.log('Initialisiere Wertentwicklung Chart mit MD3 Design...');
    
    // Überprüfe, ob das Canvas existiert
    const valueCanvas = document.getElementById('valueChart');
    if (!valueCanvas) {
      console.error('FEHLER: Wertentwicklung Canvas #valueChart nicht gefunden!');
      // Versuche, alle Canvas-Elemente zu finden, um zu debuggen
      const allCanvasElements = document.querySelectorAll('canvas');
      console.log(`Gefundene Canvas-Elemente: ${allCanvasElements.length}`);
      allCanvasElements.forEach((canvas, index) => {
        console.log(`Canvas ${index}: id=${canvas.id}, width=${canvas.width}, height=${canvas.height}`);
      });
      return;
    }
    
    console.log('Wertentwicklung Canvas gefunden:', valueCanvas);
    
    // Element bereit machen
    const container = document.getElementById('value-chart-container');
    if (container) {
      container.style.minHeight = '300px';
      // Sanfte Überblendung während des Ladens
      container.style.transition = 'opacity 0.3s ease-in-out';
      container.style.opacity = '0.6';
    }
    
    // Versuche zuerst, Daten vom Backend zu laden
    console.log('Lade Wertentwicklungs-Daten vom Backend...');
    fetch('/api/dashboard/value-development')
      .then(response => {
        console.log('API Response Status:', response.status);
        if (!response.ok) {
          throw new Error(`Netzwerkantwort war nicht ok: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        console.log('Value development data loaded:', data);
        if (!data.value_development) {
          throw new Error('API-Antwort enthält keine value_development Daten');
        }
        createValueChart(valueCanvas, data.value_development);
      })
      .catch(error => {
        console.warn('API-Fehler, verwende Fallback-Daten für Wertentwicklung:', error);
        // Fallback: Daten aus dem versteckten JSON-Element laden
        const fallbackElement = document.getElementById('value-chart-fallback-data');
        if (!fallbackElement) {
          console.error('Fallback-Element #value-chart-fallback-data nicht gefunden!');
          return;
        }
        
        try {
          console.log('Parse Fallback-Daten:', fallbackElement.textContent.substring(0, 50) + '...');
          const fallbackData = JSON.parse(fallbackElement.textContent);
          if (!fallbackData.value_development) {
            console.error('Fallback-Daten enthalten keine value_development Daten!');
            return;
          }
          createValueChart(valueCanvas, fallbackData.value_development);
        } catch (e) {
          console.error('Fehler beim Parsen der Fallback-Daten:', e);
        }
      });
  }
  
  // Werteentwicklungs-Chart erstellen (wird von initValueDevelopmentChart aufgerufen)
  function createValueChart(canvas, chartData) {
    if (!canvas || !chartData) {
      console.error('Keine Canvas oder Daten für createValueChart verfügbar!');
      return;
    }
    
    console.log('Erstelle Wertentwicklungs-Chart mit MD3-Design (vollständig neu)...');
    
    // Container zeigen
    const container = document.getElementById('value-chart-container');
    if (container) {
      container.style.opacity = '1';
    }
    
    // Kontext holen
    const ctx = canvas.getContext('2d');
    
    // Alten Chart löschen falls vorhanden
    if (window.valueChart) {
      window.valueChart.destroy();
    }
    
    // Bereich löschen
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Canvas für normale Anzeige vorbereiten
    canvas.style.opacity = '1';
    canvas.style.transform = 'translateY(0)';
    
    // Neuen Chart erstellen mit MD3 Farbpalette und erweiterten Animationen
    window.valueChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [{
          label: 'Gesamtwert',
          data: chartData.data,
          borderColor: md3Colors.primary,
          borderWidth: 2,
          backgroundColor: md3Colors.primaryAlpha, // Sanftere MD3-Fläche
          pointBackgroundColor: md3Colors.primary,
          pointBorderColor: md3Colors.surface,
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.3,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 1500,
          easing: 'easeInOutQuart'
        },
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              font: {
                family: md3Typography.bodySmall.family,
                size: parseInt(md3Typography.bodySmall.size)
              },
              padding: 16,
              usePointStyle: true,
              pointStyle: 'rectRounded'
            }
          },
          tooltip: {
          enabled: true,

            titleFont: {
              family: md3Typography.labelMedium.family,
              size: parseInt(md3Typography.labelMedium.size)
            },
            bodyFont: {
              family: md3Typography.bodySmall.family,
              size: parseInt(md3Typography.bodySmall.size)
            },
            padding: 12,
            cornerRadius: 8
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: md3Colors.outline + '40', // 25% Transparenz
              tickLength: 0
            },
            ticks: {
              font: {
                family: md3Typography.bodySmall.family,
                size: parseInt(md3Typography.bodySmall.size)
              },
              padding: 8
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              font: {
                family: md3Typography.bodySmall.family,
                size: parseInt(md3Typography.bodySmall.size)
              },
              padding: 8
            }
          }
        }
      }
    });
    
    
    console.log('Wertentwicklungs-Chart erfolgreich erstellt mit MD3-Design und Animationen');
  }
  
  // Assets nach Kategorie und Zuordnung Chart laden
  async function initCategoryAssignmentChart() {
    console.log('Category Assignment Chart wird von dashboard.html gehandhabt - überspringe dashboard-charts.js Implementation');
    return; // Überspringe diese Funktion, da die Chart bereits im main template implementiert ist
  }
  
  // Entfernt: createCategoryAssignmentChart Funktion wird nicht mehr benötigt
  // Chart wird jetzt direkt in dashboard.html gehandhabt
  
  // Chart erstellen Funktion
  function createValueChart(canvas, chartData) {
    if (!canvas || !chartData) {
      console.error('Canvas oder Daten fehlen für Wertentwicklung-Chart!');
      return;
    }
    
    console.log('Erstelle Wertentwicklung-Chart mit MD3 Design:', chartData);
    
    // Container wieder einblenden
    const container = document.getElementById('value-chart-container');
    if (container) {
      container.style.opacity = '1';
    }
    
    // Formatiere die Eurosummen in der Y-Achse
    const euroFormatter = new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
    
    // Chart erstellen mit MD3 Design
    new Chart(canvas, {
      type: 'line',
      data: {
        labels: chartData.labels || [],
        datasets: [{
          label: 'Gesamtwert',
          data: chartData.data || [],
          borderColor: md3Colors.primary,
          backgroundColor: md3Colors.primaryAlpha,
          pointBackgroundColor: md3Colors.primary,
          pointBorderColor: md3Colors.surface,
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 4,
          tension: 0.3,  // Sanfte Kurven statt gerader Linien
          fill: true,    // Füllung unter der Linie
          cubicInterpolationMode: 'monotone'  // Sanftere Kurven für nativeres Aussehen
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        md3Background: false, // Optional: Chart-Hintergrund
        animation: {
          duration: 1000,
          easing: 'easeOutQuart'
        },
        layout: {
          padding: {
            top: parseInt(md3.spacing.md) || 16,
            right: parseInt(md3.spacing.sm) || 8,
            bottom: parseInt(md3.spacing.md) || 16,
            left: parseInt(md3.spacing.md) || 16
          }
        },
        elements: {
          point: {
            radius: 4,
            hoverRadius: 4,
            hitRadius: 8,
            borderWidth: 2
          },
          line: {
            tension: 0.35,  // Sanftere Linien
            borderJoinStyle: 'round',  // Runde Linienverbindungen
            capBezierPoints: true    // Bessere Kurven
          }
        },
        interaction: {
          intersect: false,  // Tooltip beim Hover über Linien, nicht nur bei Punkten
          mode: 'index'     // Zeigt alle Werte bei gleichem X-Wert
        },
        plugins: {
          legend: {
            position: 'bottom',
            align: 'start',
            labels: {
              usePointStyle: true,
              pointStyle: 'circle',
              padding: parseInt(md3.spacing.md) || 16,
              boxWidth: 10,
              boxHeight: 10,
              font: {
                family: md3.typography.bodySmall.family,
                size: parseInt(md3.typography.bodySmall.size) || 12,
                weight: md3.typography.bodySmall.weight || 400
              }
            }
          },
          tooltip: {
            enabled: true,
            backgroundColor: md3.colors.surfaceContainerHigh || 'var(--md-sys-color-surface-container-high)',
            titleColor: md3.colors.onSurface || 'var(--md-sys-color-on-surface)',
            bodyColor: 'var(--md-sys-color-on-surface-variant)',
            padding: parseInt(md3.spacing.md) || 16,
            cornerRadius: parseInt(md3.shape.corner.md) || 12,
            boxPadding: parseInt(md3.spacing.xs) || 4,
            titleFont: {
              family: md3.typography.labelMedium.family,
              size: parseInt(md3.typography.labelMedium.size) || 14,
              weight: md3.typography.labelMedium.weight || 500
            },
            bodyFont: {
              family: md3.typography.bodySmall.family,
              size: parseInt(md3.typography.bodySmall.size) || 12,
              weight: md3.typography.bodySmall.weight || 400
            },
            callbacks: {
              label: function(context) {
                const label = context.dataset.label || '';
                const value = context.raw || 0;
                return `${label}: ${euroFormatter.format(value)}`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: md3Colors.outlineVariant + '40',  // 25% Transparenz
              tickLength: 0,
              drawBorder: false
            },
            border: {
              dash: [4, 4]  // Gestrichelte Achsenlinie
            },
            ticks: {
              padding: parseInt(md3.spacing.sm) || 8,
              font: {
                family: md3.typography.bodySmall.family,
                size: parseInt(md3.typography.bodySmall.size) || 12
              },
              callback: function(value) {
                return euroFormatter.format(value);
              }
            },
            title: {
              display: true,
              text: 'Wert in EUR',
              font: {
                family: md3.typography.labelMedium.family,
                size: parseInt(md3.typography.labelMedium.size) || 14
              },
              color: 'var(--md-sys-color-on-surface-variant)',
              padding: {
                top: 0,
                bottom: parseInt(md3.spacing.sm) || 8
              }
            }
          },
          x: {
            grid: {
              display: false,  // Keine horizontalen Gitterlinien
              drawBorder: false
            },
            ticks: {
              padding: parseInt(md3.spacing.xs) || 4,
              font: {
                family: md3.typography.bodySmall.family,
                size: parseInt(md3.typography.bodySmall.size) || 12
              },
              maxRotation: 0  // Keine Rotation der X-Achsen-Labels
            },
            border: {
              dash: [4, 4]  // Gestrichelte Achsenlinie
            }
          }
        }
      }
    });
    
    console.log('Wertentwicklung-Chart mit MD3 Design erfolgreich erstellt!');
  }
}





