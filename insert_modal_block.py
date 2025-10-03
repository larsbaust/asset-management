from pathlib import Path

path = Path(r"c:\Users\baust\CascadeProjects\Assed Managemend\app\templates\md3\layouts\locations.html")
text = path.read_text(encoding="utf-8")

modal_block = """
<div class=\"md3-floorplan-properties-modal\" id=\"floorplan-properties-modal\" aria-hidden=\"true\">
  <div class=\"md3-floorplan-properties-card\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"floorplan-properties-title\">
    <div class=\"md3-floorplan-properties-header\">
      <h3 class=\"md3-modal-title\" id=\"floorplan-properties-title\">Asset-Eigenschaften</h3>
      <p class=\"md3-modal-subtitle\" id=\"floorplan-properties-asset-name\"></p>
    </div>
    <form id=\"floorplan-properties-form\" class=\"md3-floorplan-properties-form\">
      <div class=\"md3-form-field\">
        <label class=\"md3-form-label\" for=\"floorplan-properties-radius\">Funkradius (Meter)</label>
        <input type=\"number\" id=\"floorplan-properties-radius\" class=\"md3-form-input\" min=\"0\" step=\"0.1\" placeholder=\"z. B. 30\">
        <p class=\"md3-floorplan-properties-note\">Der Radius wird als Kreis im Grundriss visualisiert. Ideal für WLAN-Router oder andere Assets mit Reichweite.</p>
      </div>
      <div class=\"md3-form-field\">
        <label class=\"md3-form-label\" for=\"floorplan-properties-note\">Notiz</label>
        <textarea id=\"floorplan-properties-note\" class=\"md3-form-input\" rows=\"3\" placeholder=\"z. B. 4,5 GHz WiFi 6\"></textarea>
      </div>
    </form>
    <div class=\"md3-floorplan-properties-actions\">
      <button type=\"button\" class=\"md3-action-btn md3-secondary-btn\" id=\"floorplan-properties-close\">
        <span class=\"material-symbols-outlined\">close</span>
        Abbrechen
      </button>
      <button type=\"button\" class=\"md3-action-btn md3-primary-btn\" id=\"floorplan-properties-save\">
        <span class=\"material-symbols-outlined\">save</span>
        Speichern
      </button>
    </div>
  </div>
</div>

"""

marker = "<!-- Edit Location Modal -->"

if modal_block.strip() in text:
    print("Modal block already present. No changes made.")
else:
    if marker not in text:
        raise SystemExit("Marker not found in locations.html")
    text = text.replace(marker, modal_block + marker, 1)
    path.write_text(text, encoding="utf-8")
    print("Modal block inserted.")
