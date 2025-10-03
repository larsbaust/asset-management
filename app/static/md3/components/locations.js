(() => {
  function init() {
    const cards = document.querySelectorAll('.md3-location-card');
    if (!cards.length) return;

    cards.forEach((card) => {
      const locationId = card.dataset.locationId;
      const viewBtn = card.querySelector('[title="Details anzeigen"]');
      const editBtn = card.querySelector('[title="Bearbeiten"]');

      if (viewBtn && typeof window.openLocationModal === 'function') {
        viewBtn.addEventListener('click', (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (locationId) {
            window.openLocationModal(locationId);
          }
        });
      }

      if (editBtn && typeof window.editLocation === 'function') {
        editBtn.addEventListener('click', (event) => {
          event.preventDefault();
          event.stopPropagation();
          if (locationId) {
            window.editLocation(locationId);
          }
        });
      }
    });

    const floorplanTrigger = document.getElementById('edit-floorplan-btn');
    if (floorplanTrigger && typeof window.openFloorplanPlannerFromEdit === 'function') {
      floorplanTrigger.addEventListener('click', (event) => {
        event.preventDefault();
        window.openFloorplanPlannerFromEdit();
      });
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
