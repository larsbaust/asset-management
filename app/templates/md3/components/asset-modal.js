// MD3 Asset-Details-Modal System
// Vollständige Implementierung mit allen Features aus asset_details.html

// Hilfsfunktion für vollständige Asset-Details-HTML
function createFullAssetDetailsHTML(asset) {
  return `
    <div style="
      padding: 0 !important;
      background: var(--md-sys-color-surface, #ffffff) !important;
      border-radius: 0 0 28px 28px !important;
      overflow: hidden !important;
    ">
      <!-- Asset-Header mit Aktions-Buttons -->
      <div style="
        padding: 24px !important;
        background: var(--md-sys-color-surface-container-lowest, #ffffff) !important;
        border-bottom: 1px solid var(--md-sys-color-outline-variant, #e0e0e0) !important;
      ">
        <div style="
          display: flex !important;
          justify-content: space-between !important;
          align-items: center !important;
          margin-bottom: 16px !important;
        ">
          <h2 style="
            margin: 0 !important;
            color: var(--md-sys-color-on-surface, #1c1b1f) !important;
            font-size: 24px !important;
            font-weight: 500 !important;
            font-family: 'Google Sans', 'Roboto', Arial, sans-serif !important;
          ">${asset.name}</h2>
          <div style="
            display: flex !important;
            gap: 8px !important;
          ">
            <button onclick="window.location.href='/assets/${asset.id}/edit'" style="
              background: var(--md-sys-color-warning-container, #fef7e0) !important;
              color: var(--md-sys-color-on-warning-container, #31270a) !important;
              border: none !important;
              padding: 8px 16px !important;
              border-radius: 20px !important;
              font-size: 14px !important;
              font-weight: 500 !important;
              cursor: pointer !important;
              display: flex !important;
              align-items: center !important;
              gap: 8px !important;
              transition: all 0.2s ease !important;
            " onmouseover="this.style.backgroundColor='var(--md-sys-color-warning, #f9c74f)'" onmouseout="this.style.backgroundColor='var(--md-sys-color-warning-container, #fef7e0)'">
              <span class="material-symbols-outlined" style="font-size: 18px !important;">edit</span>
              Bearbeiten
            </button>
            ${asset.status !== 'on_loan' ? `
            <button onclick="window.location.href='/assets/${asset.id}/loan'" style="
              background: var(--md-sys-color-primary-container, #eaddff) !important;
              color: var(--md-sys-color-on-primary-container, #21005d) !important;
              border: none !important;
              padding: 8px 16px !important;
              border-radius: 20px !important;
              font-size: 14px !important;
              font-weight: 500 !important;
              cursor: pointer !important;
              display: flex !important;
              align-items: center !important;
              gap: 8px !important;
              transition: all 0.2s ease !important;
            " onmouseover="this.style.backgroundColor='var(--md-sys-color-primary, #6750a4)'" onmouseout="this.style.backgroundColor='var(--md-sys-color-primary-container, #eaddff)'">
              <span class="material-symbols-outlined" style="font-size: 18px !important;">handshake</span>
              Ausleihen
            </button>
            ` : ''}
            <button onclick="window.location.href='/assets/${asset.id}/documents'" style="
              background: var(--md-sys-color-tertiary-container, #ffd8e4) !important;
              color: var(--md-sys-color-on-tertiary-container, #31111d) !important;
              border: none !important;
              padding: 8px 16px !important;
              border-radius: 20px !important;
              font-size: 14px !important;
              font-weight: 500 !important;
              cursor: pointer !important;
              display: flex !important;
              align-items: center !important;
              gap: 8px !important;
              transition: all 0.2s ease !important;
            " onmouseover="this.style.backgroundColor='var(--md-sys-color-tertiary, #7d5260)'" onmouseout="this.style.backgroundColor='var(--md-sys-color-tertiary-container, #ffd8e4)'">
              <span class="material-symbols-outlined" style="font-size: 18px !important;">description</span>
              Dokumente
            </button>
          </div>
        </div>
      </div>
      
      <!-- Asset-Inhalt -->
      <div style="
        display: grid !important;
        grid-template-columns: 1fr 2fr !important;
        gap: 24px !important;
        padding: 24px !important;
        max-height: 60vh !important;
        overflow-y: auto !important;
      ">
        <!-- Linke Spalte: Bild und QR-Code -->
        <div style="
          display: flex !important;
          flex-direction: column !important;
          align-items: center !important;
          gap: 20px !important;
        ">
          <!-- Asset-Bild Platzhalter -->
          <div style="
            width: 200px !important;
            height: 200px !important;
            background: var(--md-sys-color-surface-container-low, #f7f2fa) !important;
            border: 2px dashed var(--md-sys-color-outline-variant, #e0e0e0) !important;
            border-radius: 16px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            color: var(--md-sys-color-on-surface-variant, #49454f) !important;
          ">
            <span class="material-symbols-outlined" style="font-size: 48px !important; margin-bottom: 8px !important;">image</span>
            <p style="margin: 0 !important; font-size: 14px !important; text-align: center !important;">Asset-Bild<br>Platzhalter</p>
          </div>
          
          <!-- QR-Code -->
          <div style="
            background: var(--md-sys-color-surface-container-lowest, #ffffff) !important;
            border: 1px solid var(--md-sys-color-outline-variant, #e0e0e0) !important;
            border-radius: 16px !important;
            padding: 16px !important;
            text-align: center !important;
          ">
            <h4 style="
              margin: 0 0 12px 0 !important;
              color: var(--md-sys-color-primary, #6750a4) !important;
              font-size: 14px !important;
              font-weight: 500 !important;
              text-transform: uppercase !important;
              letter-spacing: 0.5px !important;
            ">QR-Code</h4>
            <div style="
              width: 120px !important;
              height: 120px !important;
              background: var(--md-sys-color-surface-container-low, #f7f2fa) !important;
              border: 1px solid var(--md-sys-color-outline-variant, #e0e0e0) !important;
              border-radius: 8px !important;
              display: flex !important;
              align-items: center !important;
              justify-content: center !important;
              margin: 0 auto 12px auto !important;
            ">
              <span class="material-symbols-outlined" style="font-size: 32px !important; color: var(--md-sys-color-on-surface-variant, #49454f) !important;">qr_code</span>
            </div>
            <button onclick="window.location.href='/assets/${asset.id}/qr'" style="
              background: var(--md-sys-color-primary-container, #eaddff) !important;
              color: var(--md-sys-color-on-primary-container, #21005d) !important;
              border: none !important;
              padding: 6px 12px !important;
              border-radius: 12px !important;
              font-size: 12px !important;
              font-weight: 500 !important;
              cursor: pointer !important;
              display: flex !important;
              align-items: center !important;
              gap: 6px !important;
              margin: 0 auto !important;
            ">
              <span class="material-symbols-outlined" style="font-size: 16px !important;">download</span>
              QR herunterladen
            </button>
          </div>
        </div>
        
        <!-- Rechte Spalte: Asset-Details -->
        ${createAssetDetailsGrid(asset)}
      </div>
    </div>
  `;
}

// Hilfsfunktion für Asset-Details-Grid
function createAssetDetailsGrid(asset) {
  return `
    <div style="
      display: grid !important;
      grid-template-columns: 1fr 1fr !important;
      gap: 16px !important;
      align-content: start !important;
    ">
      ${createDetailCard('Status', getStatusDisplay(asset.status))}
      ${createDetailCard('Artikelnummer', asset.article_number || 'N/A', true)}
      ${createDetailCard('EAN', asset.ean || 'N/A', true)}
      ${createDetailCard('Kategorie', asset.category ? asset.category.name : 'Keine Kategorie')}
      ${createDetailCard('Hersteller', asset.manufacturers && asset.manufacturers.length > 0 ? asset.manufacturers.map(m => m.name).join(', ') : 'N/A')}
      ${createDetailCard('Lieferanten', asset.suppliers && asset.suppliers.length > 0 ? asset.suppliers.map(s => s.name).join(', ') : 'N/A')}
      ${createDetailCard('Standort', asset.location_obj ? asset.location_obj.name : 'Kein Standort')}
      ${createDetailCard('Wert', asset.value ? parseFloat(asset.value).toFixed(2) + ' €' : '0.00 €', true)}
      ${createDetailCard('Anschaffungsdatum', asset.purchase_date ? new Date(asset.purchase_date).toLocaleDateString('de-DE') : 'Nicht angegeben')}
      ${createDetailCard('Beschreibung', asset.description || 'Keine Beschreibung', false, true)}
      ${createDetailCard('Zuordnungen', createAssignmentTags(asset.assignments), false, true)}
    </div>
  `;
}

// Hilfsfunktion für Detail-Karten
function createDetailCard(title, content, monospace = false, fullWidth = false) {
  return `
    <div style="
      ${fullWidth ? 'grid-column: 1 / -1 !important;' : ''}
      padding: 16px !important;
      background: var(--md-sys-color-surface-container-lowest, #ffffff) !important;
      border: 1px solid var(--md-sys-color-outline-variant, #e0e0e0) !important;
      border-radius: 16px !important;
    ">
      <h4 style="
        margin: 0 0 8px 0 !important;
        color: var(--md-sys-color-primary, #6750a4) !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
      ">${title}</h4>
      <div style="
        margin: 0 !important;
        color: var(--md-sys-color-on-surface, #1c1b1f) !important;
        font-size: 16px !important;
        font-weight: 400 !important;
        ${monospace ? 'font-family: "Roboto Mono", monospace !important;' : ''}
        ${fullWidth && title === 'Beschreibung' ? 'line-height: 1.5 !important;' : ''}
      ">${content}</div>
    </div>
  `;
}

// Hilfsfunktion für Status-Anzeige
function getStatusDisplay(status) {
  const statusConfig = {
    'active': { text: 'Aktiv', color: 'var(--md-sys-color-primary, #6750a4)' },
    'on_loan': { text: 'Ausgeliehen', color: 'var(--md-sys-color-tertiary, #7d5260)' },
    'inactive': { text: 'Inaktiv', color: 'var(--md-sys-color-error, #ba1a1a)' }
  };
  
  const config = statusConfig[status] || statusConfig['inactive'];
  
  return `
    <span style="
      background: ${config.color} !important;
      color: white !important;
      padding: 6px 16px !important;
      border-radius: 16px !important;
      font-size: 14px !important;
      font-weight: 500 !important;
    ">${config.text}</span>
  `;
}

// Hilfsfunktion für Zuordnungs-Tags
function createAssignmentTags(assignments) {
  if (!assignments || assignments.length === 0) {
    return '<span style="color: var(--md-sys-color-on-surface-variant, #49454f) !important; font-style: italic !important;">Keine Zuordnungen</span>';
  }
  
  return `
    <div style="
      display: flex !important;
      flex-wrap: wrap !important;
      gap: 8px !important;
    ">
      ${assignments.map(assignment => `
        <span style="
          background: var(--md-sys-color-tertiary-container, #ffd8e4) !important;
          color: var(--md-sys-color-on-tertiary-container, #31111d) !important;
          padding: 4px 12px !important;
          border-radius: 12px !important;
          font-size: 12px !important;
          font-weight: 500 !important;
        ">${assignment.name}</span>
      `).join('')}
    </div>
  `;
}

// Hilfsfunktion für Fehler-Anzeige
function createAssetErrorHTML() {
  return `
    <div style="
      text-align: center !important;
      padding: 40px 20px !important;
      color: var(--md-sys-color-on-surface-variant, #49454f) !important;
    ">
      <div style="
        font-size: 48px !important;
        color: var(--md-sys-color-outline, #79747e) !important;
        margin-bottom: 16px !important;
      ">📁</div>
      <p style="margin: 0 !important; font-size: 16px !important;">Asset-Details nicht verfügbar</p>
    </div>
  `;
}
