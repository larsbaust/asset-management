from pathlib import Path

TARGET = Path(r"c:/Users/baust/CascadeProjects/Assed Managemend/app/templates/md3/layouts/locations.html")

def main():
    text = TARGET.read_text(encoding="utf-8")
    updated = False

    # Remove inline onclick handler if present
    onclick_pattern = ' onclick="openFloorplanPlannerFromEdit()"'
    if onclick_pattern in text:
        text = text.replace(onclick_pattern, '', 1)
        updated = True

    # Ensure scripts block with planner script is present
    scripts_snippet = "{% block scripts %}\n{{ super() }}\n<script src=\"{{ url_for('static', filename='md3/components/floorplan-planner.js') }}\" defer></script>\n{% endblock %}\n\n"
    if "md3/components/floorplan-planner.js" not in text:
        # insert before content block declaration
        content_block = "{% block content %}"
        if content_block in text:
            text = text.replace(content_block, scripts_snippet + content_block, 1)
            updated = True
        else:
            raise RuntimeError("Content block anchor not found for scripts insertion.")

    # Inject safe event listener inside DOMContentLoaded handler
    listener_snippet = "  const floorplanButton = document.getElementById('edit-floorplan-btn');\n  if (floorplanButton) {\n    floorplanButton.addEventListener('click', function() {\n      if (typeof window.openFloorplanPlannerFromEdit === 'function') {\n        window.openFloorplanPlannerFromEdit();\n      } else {\n        console.error('❌ ERROR: Floorplan-Planner-Script ist nicht geladen.');\n      }\n    });\n  }\n\n"

    if "floorplanButton" not in text:
        anchor = "  if (window.google && window.google.maps && !map) {\n    console.log('Google Maps API available, calling initMap manually');\n    initMap();\n  }\n"
        if anchor in text:
            text = text.replace(anchor, anchor + "\n" + listener_snippet, 1)
            updated = True
        else:
            raise RuntimeError("Anchor for inserting floorplan listener not found.")

    if updated:
        TARGET.write_text(text, encoding="utf-8")
        print("locations.html updated")
    else:
        print("No changes required")

if __name__ == "__main__":
    main()
