/*
 * MD3 Floorplan Planner Frontend Logic
 * Handles canvas rendering, asset placement, autosave, and version management.
 */
(() => {
  console.log('[FloorplanPlanner] script executed');

  const state = {
    modalEl: document.getElementById('floorplan-planner-modal'),
    canvasEl: document.getElementById('floorplan-canvas'),
    placeholderEl: document.getElementById('floorplan-placeholder'),
    sidebarAssetList: document.getElementById('floorplan-asset-list'),
    sidebarVersionList: document.getElementById('floorplan-version-list'),
    statusEl: document.getElementById('floorplan-status'),
    floorplanSelect: document.getElementById('floorplan-select'),
    versionSelect: document.getElementById('floorplan-version-select'),
    uploadBtn: document.getElementById('floorplan-upload-btn'),
    newVersionBtn: document.getElementById('floorplan-new-version-btn'),
    saveBtn: document.getElementById('floorplan-save-btn'),
    setScaleBtn: document.getElementById('floorplan-set-scale-btn'),
    scaleInfoEl: document.getElementById('floorplan-scale-info'),
    assetResultsEl: document.getElementById('floorplan-asset-results'),
    assetSearchInput: document.getElementById('floorplan-asset-search'),
    assetFilterSelect: document.getElementById('floorplan-asset-filter'),
    fileInput: null,
    ctx: null,
    dragState: null,
    location: null,
    floorplans: [],
    currentFloorplan: null,
    currentRevision: null,
    backgroundImage: null,
    autosaveTimer: null,
    autosaveDelay: 1500,
    assets: [],
    isSaving: false,
    isSettingScale: false,
    scaleDraftPoints: [],
    scaleHoverPoint: null,
    scaleReference: null,
    availableAssets: [],
    assetFilter: 'all',
    assetSearchQuery: '',
    selectedAssetId: null,
    isPlacingAsset: false,
    placeholderUploadBtn: null,
    placeholderMessageEl: null,
    placeholderHelpEl: null,
    placeholderIconEl: null,
    placeholderDownloadLink: null,
    placeholderActionsEl: null,
    placeholderDownloadIconEl: null,
    placeholderDownloadLabelEl: null,
    placeholderUploadLabelEl: null,
    canvasWrapper: null,
    focusAnimation: null,
    focusAnimationFrame: null,
    contextMenuEl: null,
    contextMenuAssetId: null,
    propertiesModalEl: null,
    propertiesAssetNameEl: null,
    propertiesRadiusInput: null,
    propertiesNoteInput: null,
    propertiesSaveBtn: null,
    propertiesCloseBtn: null,
    propertiesForm: null,
  };

  const DEFAULT_PLACEHOLDER_MESSAGE = 'Hier wird der Grundriss angezeigt. Wähle eine Version oder lade einen neuen Grundriss hoch.';
  const DEFAULT_PLACEHOLDER_HELP = 'Unterstützt JPG, PNG und PDF';
  const CATEGORY_ICON_MAP = {
    hardware: '💻',
    laptop: '💻',
    notebook: '💻',
    computer: '🖥️',
    monitor: '🖥️',
    it: '🖥️',
    furniture: '🪑',
    möbel: '🪑',
    vehicle: '🚗',
    fahrzeug: '🚗',
    phone: '📱',
    telefon: '📞',
    printer: '🖨️',
    drucker: '🖨️',
    tool: '🛠️',
    werkzeug: '🛠️',
    machine: '⚙️',
    medizin: '⚕️',
    medical: '⚕️',
    default: '📍',
  };

  const MARKER_SIZE = 44;
  const MARKER_CORNER_RADIUS = 16;
  const MARKER_HIT_RADIUS = 28;
  const COVERAGE_DEFAULT_METERS_TO_PIXELS = 60;

  function ensurePlaceholderUI() {
    refreshElementReferences();
    if (!state.placeholderEl) return;

    if (state.placeholderEl.dataset.enhanced !== 'true') {
      state.placeholderEl.innerHTML = `
        <span class="material-symbols-outlined" id="floorplan-placeholder-icon">dashboard_customize</span>
        <p class="md3-floorplan-placeholder-text" id="floorplan-placeholder-message">${DEFAULT_PLACEHOLDER_MESSAGE}</p>
        <div class="md3-floorplan-placeholder-actions">
          <button type="button" class="md3-action-btn md3-primary-btn" id="floorplan-placeholder-upload">
            <span class="material-symbols-outlined">upload</span>
            <span id="floorplan-placeholder-upload-label">Grundriss-Datei hinzufügen</span>
          </button>
          <a class="md3-action-btn md3-secondary-btn" id="floorplan-placeholder-download" href="#" target="_blank" style="display: none;">
            <span class="material-symbols-outlined" id="floorplan-placeholder-download-icon">download</span>
            <span id="floorplan-placeholder-download-label">Datei öffnen</span>
          </a>
        </div>
        <p class="md3-floorplan-placeholder-help" id="floorplan-placeholder-help">${DEFAULT_PLACEHOLDER_HELP}</p>
      `;
      state.placeholderEl.dataset.enhanced = 'true';
    }

    refreshElementReferences();
    attachPlaceholderHandlers();
    attachContextMenuHandlers();
  }

  function drawCoverageCircle(assetEntry) {
    if (!state.ctx) return;
    const radiusMeters = Number(assetEntry.coverage_radius_m);
    if (!radiusMeters || Number.isNaN(radiusMeters) || radiusMeters <= 0) return;

    const scale = computeMetersToPixels();
    const radiusPx = radiusMeters * scale;
    if (!radiusPx || radiusPx <= 0) return;

    const centerX = assetEntry.position_x * state.canvasEl.width;
    const centerY = assetEntry.position_y * state.canvasEl.height;

    state.ctx.save();
    state.ctx.beginPath();
    state.ctx.fillStyle = 'rgba(103, 80, 164, 0.16)';
    state.ctx.strokeStyle = 'rgba(103, 80, 164, 0.55)';
    state.ctx.lineWidth = 2;
    state.ctx.arc(centerX, centerY, radiusPx, 0, Math.PI * 2);
    state.ctx.fill();
    state.ctx.stroke();

    if (assetEntry.coverage_note) {
      state.ctx.font = '12px "Google Sans", Roboto, sans-serif';
      state.ctx.fillStyle = 'rgba(28, 27, 31, 0.7)';
      state.ctx.textAlign = 'center';
      state.ctx.fillText(assetEntry.coverage_note.toUpperCase(), centerX, centerY + radiusPx + 16);
    }

    state.ctx.restore();
  }

  function computeMetersToPixels() {
    if (state.scaleReference?.pixelLength && state.scaleReference?.realLengthCm) {
      const meters = state.scaleReference.realLengthCm / 100;
      if (meters > 0) {
        return state.scaleReference.pixelLength / meters;
      }
    }
    return COVERAGE_DEFAULT_METERS_TO_PIXELS;
  }

  function showPlaceholder(options = {}) {
    ensurePlaceholderUI();
    refreshElementReferences();

    const {
      icon = 'dashboard_customize',
      message = DEFAULT_PLACEHOLDER_MESSAGE,
      helpText = DEFAULT_PLACEHOLDER_HELP,
      showUpload = true,
      downloadUrl = null,
      downloadLabel = 'Datei öffnen',
    } = options;

    if (state.canvasEl) {
      state.canvasEl.hidden = true;
    }
    if (!state.placeholderEl) return;

    state.placeholderEl.hidden = false;
    state.placeholderEl.style.display = '';
    state.placeholderEl.setAttribute('aria-hidden', 'false');
    state.placeholderEl.hidden = false;
    if (state.placeholderIconEl) {
      state.placeholderIconEl.textContent = icon;
    }
    if (state.placeholderMessageEl) {
      state.placeholderMessageEl.textContent = message;
    }
    if (state.placeholderHelpEl) {
      state.placeholderHelpEl.textContent = helpText;
      state.placeholderHelpEl.style.display = helpText ? '' : 'none';
    }
    if (state.placeholderUploadBtn) {
      state.placeholderUploadBtn.style.display = showUpload ? '' : 'none';
    }
    if (state.placeholderDownloadLink) {
      if (downloadUrl) {
        state.placeholderDownloadLink.href = downloadUrl;
        state.placeholderDownloadLink.style.display = '';
        if (state.placeholderDownloadIconEl) {
          state.placeholderDownloadIconEl.textContent = icon === 'picture_as_pdf' ? 'picture_as_pdf' : 'download';
        }
        if (state.placeholderDownloadLabelEl) {
          state.placeholderDownloadLabelEl.textContent = downloadLabel;
        }
      } else {
        state.placeholderDownloadLink.style.display = 'none';
      }
    }
  }

  function attachPlaceholderHandlers() {
    refreshElementReferences();
    if (state.placeholderUploadBtn && !state.placeholderUploadBtn.dataset.bound) {
      state.placeholderUploadBtn.addEventListener('click', () => triggerFileSelect('new-floorplan'));
      state.placeholderUploadBtn.dataset.bound = 'true';
    }
  }

  function hidePlaceholder() {
    if (!state.placeholderEl) return;
    state.placeholderEl.hidden = true;
    state.placeholderEl.style.display = 'none';
    state.placeholderEl.setAttribute('aria-hidden', 'true');
  }

  function getAssetIcon(asset) {
    const candidates = [
      asset?.icon,
      asset?.emoji,
      asset?.category,
      asset?.asset?.category,
      asset?.asset?.asset_type,
      asset?.asset?.name,
      asset?.display_label,
      asset?.asset?.status,
    ];

    for (const candidate of candidates) {
      if (!candidate) continue;
      const value = String(candidate).toLowerCase();
      for (const [key, icon] of Object.entries(CATEGORY_ICON_MAP)) {
        if (key === 'default') continue;
        if (value.includes(key)) {
          return icon;
        }
      }
    }

    return CATEGORY_ICON_MAP.default;
  }

  function createRoundRectPath(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  function injectPlannerStyles() {
    if (document.getElementById('floorplan-planner-inline-styles')) return;
    const style = document.createElement('style');
    style.id = 'floorplan-planner-inline-styles';
    style.textContent = `
      .md3-floorplan-placeholder-actions {
        display: flex;
        gap: 12px;
        margin-top: 12px;
        flex-wrap: wrap;
        justify-content: center;
      }
      .md3-floorplan-placeholder-help {
        font-size: 13px;
        color: var(--md-sys-color-on-surface-variant);
        margin-top: 8px;
      }
      .md3-floorplan-placeholder[hidden] {
        display: none !important;
        pointer-events: none;
      }
      .md3-floorplan-context-menu {
        position: absolute;
        z-index: 1200;
        min-width: 200px;
        background: var(--md-sys-color-surface, #fff);
        color: var(--md-sys-color-on-surface, #1c1b1f);
        border-radius: 18px;
        box-shadow: 0 8px 24px rgba(28, 27, 31, 0.18);
        padding: 8px 0;
        display: none;
      }
      .md3-floorplan-context-menu.open {
        display: block;
      }
      .md3-floorplan-context-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 16px;
        font-size: 14px;
        cursor: pointer;
        transition: background 0.18s ease;
      }
      .md3-floorplan-context-item:hover {
        background: rgba(103, 80, 164, 0.08);
      }
      .md3-floorplan-context-item .material-symbols-outlined {
        font-size: 20px;
      }
      .md3-floorplan-properties-modal {
        position: fixed;
        inset: 0;
        display: none;
        align-items: center;
        justify-content: center;
        background: rgba(28, 27, 31, 0.32);
        z-index: 1400;
      }
      .md3-floorplan-properties-modal.open {
        display: flex;
      }
      .md3-floorplan-properties-card {
        width: min(420px, 90vw);
        background: var(--md-sys-color-surface, #fff);
        color: var(--md-sys-color-on-surface, #1c1b1f);
        border-radius: 28px;
        box-shadow: 0 18px 36px rgba(28, 27, 31, 0.26);
        padding: 28px;
        display: flex;
        flex-direction: column;
        gap: 24px;
      }
      .md3-floorplan-properties-header {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .md3-floorplan-properties-actions {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
      }
      .md3-floorplan-properties-form .md3-form-field {
        margin-bottom: 18px;
      }
      .md3-floorplan-properties-note {
        font-size: 13px;
        color: var(--md-sys-color-on-surface-variant, #49454f);
        margin-top: -10px;
      }
      .md3-floorplan-coverage-note {
        font-size: 10px;
        text-align: center;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: rgba(28, 27, 31, 0.58);
        margin-top: 4px;
      }
    `;
    document.head.appendChild(style);
  }

  function refreshElementReferences() {
    state.modalEl = document.getElementById('floorplan-planner-modal');
    state.canvasEl = document.getElementById('floorplan-canvas');
    state.placeholderEl = document.getElementById('floorplan-placeholder');
    state.sidebarAssetList = document.getElementById('floorplan-asset-list');
    state.sidebarVersionList = document.getElementById('floorplan-version-list');
    state.statusEl = document.getElementById('floorplan-status');
    state.floorplanSelect = document.getElementById('floorplan-select');
    state.versionSelect = document.getElementById('floorplan-version-select');
    state.uploadBtn = document.getElementById('floorplan-upload-btn');
    state.newVersionBtn = document.getElementById('floorplan-new-version-btn');
    state.saveBtn = document.getElementById('floorplan-save-btn');
    state.setScaleBtn = document.getElementById('floorplan-set-scale-btn');
    state.scaleInfoEl = document.getElementById('floorplan-scale-info');
    state.assetResultsEl = document.getElementById('floorplan-asset-results');
    state.assetSearchInput = document.getElementById('floorplan-asset-search');
    state.assetFilterSelect = document.getElementById('floorplan-asset-filter');
    state.placeholderUploadBtn = document.getElementById('floorplan-placeholder-upload');
    state.placeholderMessageEl = document.getElementById('floorplan-placeholder-message');
    state.placeholderHelpEl = document.getElementById('floorplan-placeholder-help');
    state.placeholderIconEl = document.getElementById('floorplan-placeholder-icon');
    state.placeholderDownloadLink = document.getElementById('floorplan-placeholder-download');
    state.placeholderActionsEl = document.querySelector('#floorplan-placeholder .md3-floorplan-placeholder-actions');
    state.placeholderDownloadIconEl = document.getElementById('floorplan-placeholder-download-icon');
    state.placeholderDownloadLabelEl = document.getElementById('floorplan-placeholder-download-label');
    state.placeholderUploadLabelEl = document.getElementById('floorplan-placeholder-upload-label');
    state.canvasWrapper = document.querySelector('.md3-floorplan-canvas-wrapper');
    state.contextMenuEl = document.getElementById('floorplan-context-menu');
    state.propertiesModalEl = document.getElementById('floorplan-properties-modal');
    state.propertiesAssetNameEl = document.getElementById('floorplan-properties-asset-name');
    state.propertiesRadiusInput = document.getElementById('floorplan-properties-radius');
    state.propertiesNoteInput = document.getElementById('floorplan-properties-note');
    state.propertiesSaveBtn = document.getElementById('floorplan-properties-save');
    state.propertiesCloseBtn = document.getElementById('floorplan-properties-close');
    state.propertiesForm = document.getElementById('floorplan-properties-form');
  }

  const AUTOSAVE_MAX_HISTORY = 10;

  function init() {
    refreshElementReferences();
    injectPlannerStyles();
    ensurePlaceholderUI();
    refreshElementReferences();

    if (!state.canvasEl) {
      console.warn('[FloorplanPlanner] Canvas element not found; aborting init.');
      return;
    }

    state.ctx = state.canvasEl.getContext('2d');

    // Hidden file input reused for both upload buttons
    state.fileInput = document.createElement('input');
    state.fileInput.type = 'file';
    state.fileInput.accept = 'image/*,application/pdf';
    state.fileInput.style.display = 'none';
    document.body.appendChild(state.fileInput);

    state.fileInput.addEventListener('change', handleFileSelected);
    state.uploadBtn?.addEventListener('click', () => triggerFileSelect('new-floorplan'));
    state.placeholderUploadBtn?.addEventListener('click', () => triggerFileSelect('new-floorplan'));
    state.newVersionBtn?.addEventListener('click', () => triggerFileSelect('new-version'));
    state.saveBtn?.addEventListener('click', handleSaveAssets);
    state.setScaleBtn?.addEventListener('click', beginScaleMeasurement);

    state.floorplanSelect?.addEventListener('change', handleFloorplanChange);
    state.versionSelect?.addEventListener('change', handleVersionChange);

    setupCanvasInteractions();
    initAssetPicker();
    initPropertiesModal();
    document.addEventListener('keydown', handleGlobalKeydown);
  }

  function setupCanvasInteractions() {
    let isDragging = false;
    let dragAsset = null;
    let activePointerId = null;

    const toCanvasCoordinates = (event) => {
      const rect = state.canvasEl.getBoundingClientRect();
      const scaleX = rect.width ? state.canvasEl.width / rect.width : 1;
      const scaleY = rect.height ? state.canvasEl.height / rect.height : 1;
      const canvasX = (event.clientX - rect.left) * scaleX;
      const canvasY = (event.clientY - rect.top) * scaleY;
      const normalizedX = Math.max(0, Math.min((event.clientX - rect.left) / rect.width, 1));
      const normalizedY = Math.max(0, Math.min((event.clientY - rect.top) / rect.height, 1));
      return { canvasX, canvasY, normalizedX, normalizedY };
    };

    const handlePointerDown = (event) => {
      if (event.button === 2) {
        openContextMenu(event);
        return;
      }
      if (event.button !== 0) return;
      if (state.isSettingScale) {
        handleScalePoint(event);
        return;
      }
      if (state.isPlacingAsset && state.selectedAssetId) {
        event.preventDefault();
        placeSelectedAsset(event);
        return;
      }
      if (!state.assets || state.assets.length === 0) return;

      const { canvasX, canvasY } = toCanvasCoordinates(event);
      const hit = state.assets.find((asset) => {
        const absX = asset.position_x * state.canvasEl.width;
        const absY = asset.position_y * state.canvasEl.height;
        const dx = Math.abs(canvasX - absX);
        const dy = Math.abs(canvasY - absY);
        const half = MARKER_SIZE / 2;
        return (dx <= half && dy <= half) || Math.sqrt(dx * dx + dy * dy) <= MARKER_HIT_RADIUS;
      });

      if (hit) {
        state.contextMenuAssetId = hit.id;
        closeContextMenu();
        isDragging = true;
        dragAsset = hit;
        activePointerId = event.pointerId;
        state.dragState = {
          assetId: hit.id,
          startX: hit.position_x,
          startY: hit.position_y,
        };
        try {
          state.canvasEl.setPointerCapture(event.pointerId);
        } catch (err) {
          console.warn('Pointer capture failed', err);
        }
        state.canvasEl.style.cursor = 'grabbing';
        event.preventDefault();
      }
    };

    const handlePointerMove = (event) => {
      if (state.isSettingScale) {
        handleScaleHover(event);
        return;
      }
      if (state.isPlacingAsset && state.selectedAssetId) {
        return;
      }
      if (!isDragging || !dragAsset || (activePointerId !== null && event.pointerId !== activePointerId)) return;

      const { normalizedX, normalizedY } = toCanvasCoordinates(event);
      dragAsset.position_x = normalizedX;
      dragAsset.position_y = normalizedY;
      drawCanvas();
      scheduleAutosave();
      event.preventDefault();
    };

    const endDrag = async (event) => {
      if (!isDragging || !dragAsset) return;
      isDragging = false;
      state.canvasEl.style.cursor = '';

      if (activePointerId !== null) {
        try {
          state.canvasEl.releasePointerCapture(activePointerId);
        } catch (err) {
          /* ignore */
        }
      }
      activePointerId = null;

      try {
        await patchAssetPosition(dragAsset);
      } catch (err) {
        console.error('❌ ERROR: Failed to persist asset position', err);
        showStatus('Fehler beim Speichern der Asset-Position.', 'error');
      }

      dragAsset = null;
      state.dragState = null;
    };

    state.canvasEl.addEventListener('pointerdown', handlePointerDown);
    state.canvasEl.addEventListener('contextmenu', (event) => {
      event.preventDefault();
      openContextMenu(event);
    });
    state.canvasEl.addEventListener('pointermove', handlePointerMove);
    state.canvasEl.addEventListener('pointerup', endDrag);
    state.canvasEl.addEventListener('pointercancel', endDrag);
    state.canvasEl.addEventListener('pointerleave', (event) => {
      if (state.isSettingScale) {
        state.scaleHoverPoint = null;
        drawCanvas();
        return;
      }
      endDrag(event);
    });
    document.addEventListener('pointerdown', (event) => {
      if (!state.contextMenuEl?.classList.contains('open')) return;
      if (!state.contextMenuEl.contains(event.target)) {
        closeContextMenu();
      }
    });
    window.addEventListener('resize', closeContextMenu);
  }

  function findHitAsset(canvasX, canvasY) {
    return (state.assets || []).find((asset) => {
      const absX = asset.position_x * state.canvasEl.width;
      const absY = asset.position_y * state.canvasEl.height;
      const dx = Math.abs(canvasX - absX);
      const dy = Math.abs(canvasY - absY);
      const half = MARKER_SIZE / 2;
      return (dx <= half && dy <= half) || Math.sqrt(dx * dx + dy * dy) <= MARKER_HIT_RADIUS;
    });
  }

  function openContextMenu(event) {
    if (!state.contextMenuEl || !state.canvasEl) return;

    const rect = state.canvasEl.getBoundingClientRect();
    const scaleX = rect.width ? state.canvasEl.width / rect.width : 1;
    const scaleY = rect.height ? state.canvasEl.height / rect.height : 1;
    const canvasX = (event.clientX - rect.left) * scaleX;
    const canvasY = (event.clientY - rect.top) * scaleY;

    const hit = findHitAsset(canvasX, canvasY);
    if (!hit) {
      closeContextMenu();
      return;
    }

    state.contextMenuAssetId = hit.id;

    const wrapperRect = state.canvasWrapper?.getBoundingClientRect();
    const wrapperX = wrapperRect ? wrapperRect.left : 0;
    const wrapperY = wrapperRect ? wrapperRect.top : 0;

    state.contextMenuEl.style.left = `${Math.max(0, event.clientX - wrapperX)}px`;
    state.contextMenuEl.style.top = `${Math.max(0, event.clientY - wrapperY)}px`;
    state.contextMenuEl.classList.add('open');
  }

  function closeContextMenu() {
    if (state.contextMenuEl) {
      state.contextMenuEl.classList.remove('open');
    }
  }

  function attachContextMenuHandlers() {
    refreshElementReferences();
    if (!state.contextMenuEl) return;

    state.contextMenuEl.querySelectorAll('.md3-floorplan-context-item').forEach((item) => {
      item.addEventListener('click', () => {
        const action = item.dataset.action;
        const assetEntry = findAssetEntry(state.contextMenuAssetId);
        if (!assetEntry) {
          closeContextMenu();
          return;
        }

        if (action === 'focus') {
          focusAsset(assetEntry);
        } else if (action === 'properties') {
          openPropertiesModal(assetEntry);
        } else if (action === 'delete') {
          deleteAssetPlacement(assetEntry);
        }
        closeContextMenu();
      });
    });
  }

  function findAssetEntry(assetEntryId) {
    if (!assetEntryId) return null;
    return (state.assets || []).find((entry) => Number(entry.id) === Number(assetEntryId));
  }

  function initPropertiesModal() {
    refreshElementReferences();
    if (!state.propertiesModalEl) return;

    const closeModal = () => {
      state.propertiesModalEl.classList.remove('open');
      state.propertiesModalEl.setAttribute('aria-hidden', 'true');
      state.propertiesModalEl.dataset.assetId = '';
      if (state.propertiesRadiusInput) state.propertiesRadiusInput.value = '';
      if (state.propertiesNoteInput) state.propertiesNoteInput.value = '';
    };

    state.propertiesCloseBtn?.addEventListener('click', closeModal);
    state.propertiesModalEl?.addEventListener('click', (event) => {
      if (event.target === state.propertiesModalEl) {
        closeModal();
      }
    });

    state.propertiesSaveBtn?.addEventListener('click', async () => {
      const assetId = Number(state.propertiesModalEl?.dataset.assetId);
      const assetEntry = findAssetEntry(assetId);
      if (!assetEntry) {
        closeModal();
        return;
      }

      const radius = state.propertiesRadiusInput?.value ? Number(state.propertiesRadiusInput.value) : null;
      const note = state.propertiesNoteInput?.value?.trim() || null;
      const metadata = { ...(assetEntry.metadata || {}) };

      if (radius !== null && !Number.isNaN(radius) && radius >= 0) {
        metadata.coverage_radius_m = radius;
      } else {
        delete metadata.coverage_radius_m;
      }

      if (note) {
        metadata.coverage_note = note;
      } else {
        delete metadata.coverage_note;
      }

      try {
        const response = await fetch(`/api/floorplan-assets/${assetEntry.id}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrfToken || '',
          },
          body: JSON.stringify({
            coverage_radius_m: radius,
            coverage_note: note,
            metadata,
          }),
        });

        if (!response.ok) {
          throw new Error('Serverfehler beim Speichern der Eigenschaften');
        }

        const payload = await response.json().catch(() => ({}));
        if (payload?.asset) {
          const idx = state.assets.findIndex((entry) => Number(entry.id) === Number(payload.asset.id));
          if (idx !== -1) {
            state.assets[idx] = {
              ...state.assets[idx],
              ...payload.asset,
              metadata: payload.asset.metadata || {},
            };
          }
        } else {
          assetEntry.coverage_radius_m = radius;
          assetEntry.coverage_note = note;
          assetEntry.metadata = metadata;
        }

        drawCanvas();
        showStatus('Eigenschaften gespeichert.', 'success');
        closeModal();
      } catch (err) {
        console.error('❌ ERROR: Failed to save asset properties', err);
        showStatus('Fehler beim Speichern der Eigenschaften.', 'error');
      }
    });
  }

  function openPropertiesModal(assetEntry) {
    refreshElementReferences();
    if (!state.propertiesModalEl) return;

    state.propertiesModalEl.dataset.assetId = assetEntry.id;
    if (state.propertiesAssetNameEl) {
      state.propertiesAssetNameEl.textContent = assetEntry?.asset?.name || assetEntry.display_label || `Asset #${assetEntry.asset_id}`;
    }
    if (state.propertiesRadiusInput) {
      state.propertiesRadiusInput.value = assetEntry.coverage_radius_m ?? assetEntry.metadata?.coverage_radius_m ?? '';
    }
    if (state.propertiesNoteInput) {
      state.propertiesNoteInput.value = assetEntry.coverage_note ?? assetEntry.metadata?.coverage_note ?? '';
    }

    state.propertiesModalEl.classList.add('open');
    state.propertiesModalEl.setAttribute('aria-hidden', 'false');
  }

  function beginScaleMeasurement() {
    if (!state.currentRevision) {
      showStatus('Bitte zuerst eine Version laden.', 'info');
      return;
    }

    state.isSettingScale = true;
    state.scaleDraftPoints = [];
    state.scaleHoverPoint = null;
    showStatus('Maßstab setzen: Klicke auf den Startpunkt der Referenzlinie.', 'info');
    state.canvasEl?.classList.add('is-setting-scale');
  }

  function cancelScaleMeasurement(message, type = 'info') {
    state.isSettingScale = false;
    state.scaleDraftPoints = [];
    state.scaleHoverPoint = null;
    state.canvasEl?.classList.remove('is-setting-scale');
    if (message) {
      showStatus(message, type);
    } else {
      clearStatus();
    }
    drawCanvas();
  }

  function handleScalePoint(event) {
    if (!state.isSettingScale || !state.canvasEl) return;
    const rect = state.canvasEl.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const point = { x, y };

    if (state.scaleDraftPoints.length === 0) {
      state.scaleDraftPoints.push(point);
      showStatus('Klicke auf den Endpunkt der Referenzlinie.', 'info');
    } else if (state.scaleDraftPoints.length === 1) {
      state.scaleDraftPoints.push(point);
      const start = state.scaleDraftPoints[0];
      const end = state.scaleDraftPoints[1];
      const pixelLength = Math.hypot(end.x - start.x, end.y - start.y);
      if (pixelLength < 10) {
        cancelScaleMeasurement('Linie ist zu kurz. Bitte erneut versuchen.', 'error');
        return;
      }

      const input = prompt('Reale Länge in Zentimetern (z. B. 420):');
      const realLength = input ? parseFloat(input.replace(',', '.')) : NaN;
      if (!input || Number.isNaN(realLength) || realLength <= 0) {
        cancelScaleMeasurement('Maßstab wurde abgebrochen – ungültige Eingabe.', 'error');
        return;
      }

      finalizeScaleMeasurement(pixelLength, realLength);
    }

    drawCanvas();
  }

  function handleScaleHover(event) {
    if (!state.isSettingScale || !state.canvasEl) return;
    if (state.scaleDraftPoints.length === 0) return;
    const rect = state.canvasEl.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    state.scaleHoverPoint = { x, y };
    drawCanvas();
  }

  async function finalizeScaleMeasurement(pixelLength, realLengthCm) {
    if (!state.currentRevision) {
      cancelScaleMeasurement('Keine Revision ausgewählt.', 'error');
      return;
    }

    showStatus('Maßstab wird gespeichert...', 'info');
    try {
      const response = await fetch(`/api/floorplan-revisions/${state.currentRevision.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.csrfToken || '',
        },
        body: JSON.stringify({
          scale_line_length_px: Number(pixelLength.toFixed(4)),
          scale_real_length_cm: Number(realLengthCm.toFixed(4)),
        }),
      });

      if (!response.ok) {
        throw new Error('Serverfehler beim Speichern des Maßstabs');
      }

      const data = await response.json();
      const revision = data.revision || state.currentRevision;
      state.currentRevision.scale_line_length_px = revision.scale_line_length_px;
      state.currentRevision.scale_real_length_cm = revision.scale_real_length_cm;
      state.scaleReference = {
        pixelLength: revision.scale_line_length_px,
        realLengthCm: revision.scale_real_length_cm,
      };
      updateScaleInfo();
      cancelScaleMeasurement('Maßstab gespeichert.', 'success');
    } catch (err) {
      console.error('❌ ERROR: Failed to save scale', err);
      cancelScaleMeasurement('Fehler beim Speichern des Maßstabs.', 'error');
    }
  }

  async function patchAssetPosition(asset) {
    if (!asset?.id) return;
    const payload = {
      position_x: Number(asset.position_x.toFixed(4)),
      position_y: Number(asset.position_y.toFixed(4)),
    };

    await fetch(`/api/floorplan-assets/${asset.id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.csrfToken || '',
      },
      body: JSON.stringify(payload),
    });
  }

  function triggerFileSelect(mode) {
    state.fileInput.dataset.mode = mode;
    state.fileInput.value = '';
    state.fileInput.click();
  }

  async function handleFileSelected(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    const mode = event.target.dataset.mode;
    try {
      if (mode === 'new-floorplan') {
        await uploadNewFloorplan(file);
      } else if (mode === 'new-version') {
        await uploadNewVersion(file);
      }
    } catch (err) {
      console.error('❌ ERROR: Upload failed', err);
      showStatus('Upload fehlgeschlagen. Bitte erneut versuchen.', 'error');
    }
  }

  async function uploadNewFloorplan(file) {
    if (!state.location) return;
    const formData = new FormData();
    formData.append('name', file.name);
    formData.append('file', file);
    formData.append('description', '');

    const response = await fetch(`/api/locations/${state.location.id}/floorplans`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': window.csrfToken || '',
      },
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || 'Unbekannter Fehler beim Anlegen des Grundrisses.');
    }

    showStatus('Grundriss hinzugefügt.', 'success');
    await loadFloorplans(state.location.id);
  }

  async function uploadNewVersion(file) {
    if (!state.currentFloorplan) {
      showStatus('Bitte zuerst einen Grundriss auswählen.', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`/api/floorplans/${state.currentFloorplan.id}/revisions`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': window.csrfToken || '',
      },
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || 'Unbekannter Fehler beim Anlegen der Version.');
    }

    showStatus('Neue Version erstellt.', 'success');
    await loadFloorplans(state.location.id, { floorplanId: state.currentFloorplan.id });
  }

  function openFloorplanPlannerFromEdit() {
    console.log('[FloorplanPlanner] openFloorplanPlannerFromEdit triggered');
    const locationId = document.getElementById('edit-location-id')?.value;
    if (!locationId) {
      showStatus('Standort-ID fehlt. Bitte zunächst speichern.', 'error');
      return;
    }
    const location = findLocation(Number(locationId));
    if (!location) {
      showStatus('Standortdaten nicht gefunden.', 'error');
      return;
    }
    openFloorplanPlanner(location.id, location);
  }

  function findLocation(id) {
    if (!window.locationsData || !Array.isArray(window.locationsData)) return null;
    return window.locationsData.find((loc) => Number(loc.id) === Number(id));
  }

  async function openFloorplanPlanner(locationId, locationData = null) {
    state.location = locationData || findLocation(locationId) || { id: locationId, name: `Standort #${locationId}` };
    document.getElementById('floorplan-modal-location').textContent = state.location.name || `Standort #${locationId}`;

    state.modalEl.style.display = 'flex';
    document.body.style.overflow = 'hidden';

    resetPlannerState();
    await loadLocationAssets(locationId);
    await loadFloorplans(locationId);
  }

  function resetPlannerState() {
    state.floorplans = [];
    state.currentFloorplan = null;
    state.currentRevision = null;
    state.assets = [];
    state.backgroundImage = null;
    state.scaleReference = null;
    state.scaleDraftPoints = [];
    state.scaleHoverPoint = null;
    state.isSettingScale = false;
    state.availableAssets = [];
    state.assetFilter = 'all';
    state.assetSearchQuery = '';
    state.selectedAssetId = null;
    state.isPlacingAsset = false;

    if (state.floorplanSelect) state.floorplanSelect.innerHTML = '';
    if (state.versionSelect) state.versionSelect.innerHTML = '';
    if (state.sidebarAssetList) state.sidebarAssetList.innerHTML = '';
    if (state.sidebarVersionList) state.sidebarVersionList.innerHTML = '';
    if (state.assetResultsEl) state.assetResultsEl.innerHTML = '<p class="md3-floorplan-empty">Keine Assets gefunden.</p>';
    if (state.assetSearchInput) state.assetSearchInput.value = '';
    if (state.assetFilterSelect) state.assetFilterSelect.value = 'all';
    if (state.scaleInfoEl) state.scaleInfoEl.textContent = 'Maßstab nicht gesetzt';
    state.canvasEl?.classList.remove('is-placing-asset');

    showPlaceholder();
    clearStatus();
    stopFocusAnimation();
  }

  async function loadFloorplans(locationId, options = {}) {
    showStatus('Grundrisse werden geladen...', 'info');

    const response = await fetch(`/api/locations/${locationId}/floorplans`);
    if (!response.ok) {
      showStatus('Fehler beim Laden der Grundrisse.', 'error');
      return;
    }

    const payload = await response.json();
    state.floorplans = payload.floorplans || [];

    if (state.floorplans.length === 0) {
      showPlaceholder({
        icon: 'grid_view',
        message: 'Noch keine Grundrisse vorhanden. Füge jetzt einen Grundriss hinzu, um zu starten.',
        helpText: 'Unterstützt JPG, PNG und PDF',
        showUpload: true,
      });
      showStatus('Noch keine Grundrisse vorhanden. Bitte einen neuen Grundriss hochladen.', 'info');
      return;
    }

    populateFloorplanSelect(options.floorplanId);
    showStatus('Grundrisse geladen.', 'success');
  }

  function populateFloorplanSelect(preferredId = null) {
    if (!state.floorplanSelect) return;

    state.floorplanSelect.innerHTML = '';
    state.floorplans.forEach((fp) => {
      const option = document.createElement('option');
      option.value = fp.id;
      option.textContent = fp.name;
      state.floorplanSelect.appendChild(option);
    });

    let floorplanToSelect = state.floorplans[0];
    if (preferredId) {
      const preferred = state.floorplans.find((fp) => fp.id === preferredId);
      if (preferred) floorplanToSelect = preferred;
    }

    state.floorplanSelect.value = floorplanToSelect.id;
    handleFloorplanChange();
  }

  function handleFloorplanChange() {
    const floorplanId = Number(state.floorplanSelect.value);
    state.currentFloorplan = state.floorplans.find((fp) => Number(fp.id) === floorplanId) || null;

    if (!state.currentFloorplan) {
      showStatus('Grundriss konnte nicht geladen werden.', 'error');
      return;
    }

    populateVersionSelect();
  }

  function populateVersionSelect() {
    if (!state.versionSelect || !state.currentFloorplan) return;

    state.versionSelect.innerHTML = '';
    const revisions = state.currentFloorplan.revisions || [];

    if (revisions.length === 0) {
      showStatus('Keine Versionen gefunden. Bitte neue Version hochladen.', 'info');
      showPlaceholder({
        icon: 'upload_file',
        message: 'Für diesen Grundriss existieren noch keine Versionen. Lade eine Version hoch, um mit dem Planer zu arbeiten.',
        showUpload: true,
        helpText: 'Unterstützt JPG, PNG und PDF',
      });
      return;
    }

    revisions.forEach((rev) => {
      const option = document.createElement('option');
      option.value = rev.id;
      option.textContent = `Version ${rev.version_number}`;
      state.versionSelect.appendChild(option);
    });

    const latest = revisions[revisions.length - 1];
    state.versionSelect.value = latest.id;
    handleVersionChange();
  }

  function handleVersionChange() {
    const revisionId = Number(state.versionSelect.value);
    const revisions = state.currentFloorplan.revisions || [];
    state.currentRevision = revisions.find((rev) => Number(rev.id) === revisionId) || null;

    if (!state.currentRevision) {
      showStatus('Version konnte nicht geladen werden.', 'error');
      return;
    }

    renderVersionSidebar();
    loadRevisionCanvas();
  }

  function renderVersionSidebar() {
    if (!state.sidebarVersionList) return;

    state.sidebarVersionList.innerHTML = '';
    const revisions = state.currentFloorplan.revisions || [];
    revisions.forEach((rev) => {
      const item = document.createElement('div');
      item.className = 'md3-floorplan-version-item';
      item.textContent = `v${rev.version_number} · ${formatDate(rev.created_at)}`;
      if (rev.id === state.currentRevision.id) {
        item.classList.add('active');
      }
      item.addEventListener('click', () => {
        state.versionSelect.value = rev.id;
        handleVersionChange();
      });
      state.sidebarVersionList.appendChild(item);
    });
  }

  function formatDate(input) {
    if (!input) return '';
    const date = new Date(input);
    return date.toLocaleDateString('de-DE', { year: 'numeric', month: 'short', day: 'numeric' });
  }

  async function loadRevisionCanvas() {
    state.assets = (state.currentRevision.assets || []).map((asset) => ({
      ...asset,
      metadata: asset.metadata || {},
    }));
    updateAssetPlacementStatuses();
    renderAssetList();
    renderAssetResults();

    const imageUrl = state.currentRevision.preview_url || state.currentRevision.file_url;
    if (!imageUrl || state.currentRevision.mimetype?.includes('pdf')) {
      showPlaceholder({
        icon: 'picture_as_pdf',
        message: 'Diese Version ist eine PDF-Datei. Lade sie herunter, um sie anzusehen, oder füge eine neue Version hinzu.',
        showUpload: true,
        downloadUrl: state.currentRevision.file_url,
        downloadLabel: 'PDF herunterladen',
      });
      showStatus('PDF-Dateien können im Browser nicht gerendert werden.', 'info');
      return;
    }

    await loadBackgroundImage(imageUrl);
    resizeCanvasToImage();
    drawCanvas();
    showStatus('Version geladen.', 'success');
  }

  function renderAssetList() {
    if (!state.sidebarAssetList) return;
    state.sidebarAssetList.innerHTML = '';

    if (!state.assets || state.assets.length === 0) {
      state.sidebarAssetList.innerHTML = '<p class="md3-floorplan-empty">Keine Assets positioniert.</p>';
      return;
    }

    state.assets.forEach((asset) => {
      const item = document.createElement('div');
      item.className = 'md3-floorplan-asset-item';
      item.innerHTML = `
        <div class="md3-floorplan-asset-title">${asset.display_label || asset?.asset?.name || 'Asset'}</div>
        <div class="md3-floorplan-asset-meta">
          <span>Pos: ${(asset.position_x * 100).toFixed(1)}%, ${(asset.position_y * 100).toFixed(1)}%</span>
          ${asset.asset?.serial_number ? `<span>SN: ${asset.asset.serial_number}</span>` : ''}
        </div>
        <div class="md3-floorplan-asset-actions">
          <button type="button" class="md3-action-btn md3-secondary-btn" data-action="jump" data-id="${asset.id}">
            <span class="material-symbols-outlined">my_location</span>
            Fokus
          </button>
          <button type="button" class="md3-action-btn md3-error-btn" data-action="delete" data-id="${asset.id}">
            <span class="material-symbols-outlined">delete</span>
            Entfernen
          </button>
        </div>
      `;
      item.querySelector('[data-action="jump"]').addEventListener('click', () => focusAsset(asset));
      item.querySelector('[data-action="delete"]').addEventListener('click', () => deleteAssetPlacement(asset));
      state.sidebarAssetList.appendChild(item);
    });
  }

  function updateAssetPlacementStatuses() {
    if (!Array.isArray(state.availableAssets)) return;
    const placedIds = new Set((state.assets || []).map((entry) => entry.asset_id || entry.asset?.id));
    state.availableAssets.forEach((asset) => {
      asset.isPlaced = placedIds.has(asset.id);
    });
    if (state.selectedAssetId && state.availableAssets.every((asset) => asset.id !== state.selectedAssetId)) {
      state.selectedAssetId = null;
      state.isPlacingAsset = false;
      state.canvasEl?.classList.remove('is-placing-asset');
    }
  }

  function renderAssetResults() {
    if (!state.assetResultsEl) return;

    if (!Array.isArray(state.availableAssets) || state.availableAssets.length === 0) {
      state.assetResultsEl.innerHTML = '<p class="md3-floorplan-empty">Keine Assets gefunden.</p>';
      return;
    }

    const results = filterAssetsForDisplay();

    if (results.length === 0) {
      state.assetResultsEl.innerHTML = '<p class="md3-floorplan-empty">Keine Assets entsprechen den Filtern.</p>';
      return;
    }

    state.assetResultsEl.innerHTML = '';

    results.forEach((asset) => {
      const item = document.createElement('div');
      item.className = 'md3-floorplan-asset-result';
      if (asset.isPlaced) item.classList.add('is-placed');
      if (asset.id === state.selectedAssetId) item.classList.add('is-selected');

      const actionIcon = asset.isPlaced ? 'check_circle' : 'add_location_alt';
      const actionLabel = asset.isPlaced ? 'Platziert' : 'Platzieren';
      const metaParts = [];
      if (asset.serial_number) metaParts.push(`SN: ${escapeHtml(asset.serial_number)}`);
      if (asset.article_number) metaParts.push(`Artikel: ${escapeHtml(asset.article_number)}`);
      if (asset.category) metaParts.push(`Kategorie: ${escapeHtml(asset.category)}`);
      if (asset.on_loan) metaParts.push('Ausgeliehen');

      const statusHtml = asset.status_display
        ? `<span class="md3-floorplan-asset-status">${escapeHtml(asset.status_display)}</span>`
        : '';
      const metaHtml = metaParts.length
        ? `<div class="md3-floorplan-asset-meta">${metaParts.join(' · ')}</div>`
        : '';

      item.innerHTML = `
        <div class="md3-floorplan-asset-result-header">
          <span class="md3-floorplan-asset-name">${escapeHtml(asset.name)}</span>
          <span class="md3-floorplan-asset-action">
            <span class="material-symbols-outlined">${actionIcon}</span>
            ${actionLabel}
          </span>
        </div>
        ${statusHtml}
        ${metaHtml}
      `;

      item.addEventListener('click', () => handleAssetSelection(asset.id));
      state.assetResultsEl.appendChild(item);
    });
  }

  function filterAssetsForDisplay() {
    const term = (state.assetSearchQuery || '').toLowerCase();
    return state.availableAssets.filter((asset) => {
      if (state.assetFilter === 'unplaced' && asset.isPlaced) return false;
      if (state.assetFilter === 'placed' && !asset.isPlaced) return false;

      if (term) {
        const haystack = [asset.name, asset.serial_number, asset.article_number, asset.category]
          .filter(Boolean)
          .join(' ') 
          .toLowerCase();
        if (!haystack.includes(term)) return false;
      }

      return true;
    });
  }

  function handleAssetSelection(assetId) {
    const asset = state.availableAssets.find((entry) => entry.id === assetId);
    if (!asset) return;

    if (asset.isPlaced) {
      state.selectedAssetId = assetId;
      state.isPlacingAsset = false;
      state.canvasEl?.classList.remove('is-placing-asset');
      renderAssetResults();
      showStatus('Asset ist bereits platziert. Ziehe den Punkt im Grundriss, um die Position anzupassen.', 'info');
      return;
    }

    startAssetPlacement(assetId);
  }

  async function deleteAssetPlacement(assetEntry) {
    if (!assetEntry?.id) return;
    const confirmed = confirm('Soll dieses Asset wirklich vom Grundriss entfernt werden?');
    if (!confirmed) return;

    try {
      const response = await fetch(`/api/floorplan-assets/${assetEntry.id}`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': window.csrfToken || '',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      state.assets = state.assets.filter((entry) => entry.id !== assetEntry.id);
      updateAssetPlacementStatuses();
      renderAssetList();
      renderAssetResults();
      drawCanvas();
      showStatus('Asset wurde entfernt.', 'success');
    } catch (err) {
      console.error('❌ ERROR: Failed to delete asset placement', err);
      showStatus('Asset konnte nicht entfernt werden.', 'error');
    }
  }

  function focusAsset(assetEntry) {
    if (!assetEntry) return;
    showStatus('Asset im Grundriss hervorgehoben. Du kannst den Punkt jetzt verschieben.', 'info');
    const assetId = assetEntry.asset_id || assetEntry.asset?.id || assetEntry.id || null;
    state.selectedAssetId = assetId;
    state.isPlacingAsset = false;
    state.canvasEl?.classList.remove('is-placing-asset');
    startFocusAnimation(assetEntry);
    state.canvasEl?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    drawCanvas();
  }

  function escapeHtml(value) {
    if (!value) return '';
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function startAssetPlacement(assetId) {
    state.selectedAssetId = assetId;
    state.isPlacingAsset = true;
    state.canvasEl?.classList.add('is-placing-asset');
    const asset = state.availableAssets.find((entry) => entry.id === assetId);
    const assetName = asset ? asset.name : 'Asset';
    showStatus(`Klicke in den Grundriss, um "${assetName}" zu platzieren. ESC zum Abbrechen.`, 'info');
    renderAssetResults();
  }

  function cancelAssetPlacement(showMessage = true) {
    if (!state.isPlacingAsset && !state.selectedAssetId) return;
    state.isPlacingAsset = false;
    state.selectedAssetId = null;
    state.canvasEl?.classList.remove('is-placing-asset');
    if (showMessage) {
      showStatus('Asset-Platzierung abgebrochen.', 'info');
    }
    renderAssetResults();
  }

  async function placeSelectedAsset(event) {
    if (!state.isPlacingAsset || !state.selectedAssetId || !state.currentRevision) return;
    const asset = state.availableAssets.find((entry) => entry.id === state.selectedAssetId);
    if (!asset) {
      cancelAssetPlacement(false);
      return;
    }
    if (asset.isPlaced) {
      cancelAssetPlacement(false);
      showStatus('Asset ist bereits platziert.', 'info');
      return;
    }

    const rect = state.canvasEl.getBoundingClientRect();
    const normalizedX = Math.max(0, Math.min((event.clientX - rect.left) / rect.width, 1));
    const normalizedY = Math.max(0, Math.min((event.clientY - rect.top) / rect.height, 1));

    showStatus('Asset wird platziert...', 'info');

    try {
      const response = await fetch(`/api/floorplan-revisions/${state.currentRevision.id}/assets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.csrfToken || '',
        },
        body: JSON.stringify({
          asset_id: state.selectedAssetId,
          position_x: Number(normalizedX.toFixed(4)),
          position_y: Number(normalizedY.toFixed(4)),
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const assetEntry = data.asset;
      if (assetEntry) {
        state.assets.push(assetEntry);
        updateAssetPlacementStatuses();
        renderAssetList();
        renderAssetResults();
        drawCanvas();
      }
      showStatus('Asset wurde platziert.', 'success');
    } catch (err) {
      console.error('❌ ERROR: Asset placement failed', err);
      showStatus('Asset konnte nicht platziert werden.', 'error');
    } finally {
      cancelAssetPlacement(false);
    }
  }

  function initAssetPicker() {
    state.assetSearchInput?.addEventListener('input', handleAssetSearchInput);
    state.assetFilterSelect?.addEventListener('change', handleAssetFilterChange);
  }

  function handleAssetSearchInput(event) {
    state.assetSearchQuery = event.target.value.trim();
    renderAssetResults();
  }

  function handleAssetFilterChange(event) {
    state.assetFilter = event.target.value;
    renderAssetResults();
  }

  async function loadLocationAssets(locationId) {
    if (!locationId) return;
    try {
      const response = await fetch(`/api/locations/${locationId}/assets`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      state.availableAssets = data.assets || [];
      updateAssetPlacementStatuses();
      renderAssetResults();
    } catch (err) {
      console.error('❌ ERROR: Failed to load location assets', err);
      state.availableAssets = [];
      if (state.assetResultsEl) {
        state.assetResultsEl.innerHTML = '<p class="md3-floorplan-empty">Assets konnten nicht geladen werden.</p>';
      }
      showStatus('Assets konnten nicht geladen werden.', 'error');
    }
  }

  function handleGlobalKeydown(event) {
    if (event.key === 'Escape') {
      if (state.isPlacingAsset || state.selectedAssetId) {
        cancelAssetPlacement();
      }
      if (state.isSettingScale) {
        cancelScaleMeasurement('Maßstabsmessung abgebrochen.', 'info');
      }
    }
  }

  async function loadBackgroundImage(url) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        state.backgroundImage = img;
        resolve();
      };
      img.onerror = (err) => {
        console.error('❌ ERROR: Failed to load background image', err);
        showStatus('Grundriss konnte nicht geladen werden.', 'error');
        reject(err);
      };
      img.src = url;
    });
  }

  function resizeCanvasToImage() {
    if (!state.backgroundImage) return;
    const maxWidth = 1200;
    const scale = Math.min(1, maxWidth / state.backgroundImage.width);

    state.canvasEl.width = Math.floor(state.backgroundImage.width * scale);
    state.canvasEl.height = Math.floor(state.backgroundImage.height * scale);

    state.canvasEl.hidden = false;
    hidePlaceholder();
  }

  function drawCanvas() {
    if (!state.ctx) return;
    state.ctx.clearRect(0, 0, state.canvasEl.width, state.canvasEl.height);

    if (state.backgroundImage) {
      state.ctx.drawImage(state.backgroundImage, 0, 0, state.canvasEl.width, state.canvasEl.height);
    }

    if (state.assets && state.assets.length > 0) {
      state.assets.forEach((asset) => {
        const x = asset.position_x * state.canvasEl.width;
        const y = asset.position_y * state.canvasEl.height;
        drawAssetMarker(x, y, asset);
      });
    }

    drawFocusPulse();
    drawScaleOverlay();
  }

  function drawAssetMarker(x, y, asset) {
    const ctx = state.ctx;
    if (!ctx) return;

    const isSelected = !!(state.selectedAssetId && (asset.asset_id === state.selectedAssetId || asset.asset?.id === state.selectedAssetId || asset.id === state.selectedAssetId));
    const size = MARKER_SIZE;
    const half = size / 2;

    ctx.save();
    ctx.translate(x, y);
    ctx.beginPath();
    if (typeof ctx.roundRect === 'function') {
      ctx.roundRect(-half, -half, size, size, MARKER_CORNER_RADIUS);
    } else {
      createRoundRectPath(ctx, -half, -half, size, size, MARKER_CORNER_RADIUS);
    }

    const gradient = ctx.createLinearGradient(0, -half, 0, half);
    if (isSelected) {
      gradient.addColorStop(0, '#5B4EBF');
      gradient.addColorStop(1, '#352975');
    } else {
      gradient.addColorStop(0, '#6750A4');
      gradient.addColorStop(1, '#4F378B');
    }
    ctx.shadowColor = 'rgba(0, 0, 0, 0.24)';
    ctx.shadowBlur = 14;
    ctx.shadowOffsetY = 8;
    ctx.fillStyle = gradient;
    ctx.fill();

    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;
    ctx.shadowOffsetY = 0;

    ctx.lineWidth = isSelected ? 3.4 : 2.4;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.88)';
    ctx.stroke();

    ctx.fillStyle = '#FFFFFF';
    ctx.font = '26px "Segoe UI Emoji", "Noto Color Emoji", "Roboto", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(getAssetIcon(asset), 0, -6);

    ctx.font = 'bold 11px "Roboto", sans-serif';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
    ctx.fillText(deriveAssetLabel(asset), 0, size / 2 - 10);

    ctx.restore();
  }

  function drawFocusPulse() {
    if (!state.focusAnimation || !state.canvasEl || !state.ctx) return;
    const { assetId, start } = state.focusAnimation;
    const target = state.assets?.find((entry) => {
      const id = entry.asset_id || entry.asset?.id || entry.id;
      return id === assetId;
    });
    if (!target) {
      stopFocusAnimation();
      return;
    }

    const elapsed = performance.now() - start;
    if (elapsed > 1800) {
      stopFocusAnimation();
      return;
    }

    const x = target.position_x * state.canvasEl.width;
    const y = target.position_y * state.canvasEl.height;
    const cycle = 900;
    const phase = (elapsed % cycle) / cycle;
    const baseRadius = MARKER_SIZE / 2 + 8;
    const extraRadius = 22;
    const radius = baseRadius + extraRadius * phase;
    const alpha = 0.42 * (1 - phase);

    state.ctx.save();
    state.ctx.beginPath();
    state.ctx.arc(x, y, radius, 0, Math.PI * 2);
    state.ctx.strokeStyle = `rgba(103, 80, 164, ${alpha.toFixed(3)})`;
    state.ctx.lineWidth = 4;
    state.ctx.stroke();
    state.ctx.restore();

    state.focusAnimationFrame = requestAnimationFrame(drawCanvas);
  }

  function startFocusAnimation(assetEntry) {
    stopFocusAnimation();
    const assetId = assetEntry.asset_id || assetEntry.asset?.id || assetEntry.id;
    if (!assetId) return;
    state.focusAnimation = {
      assetId,
      start: performance.now(),
    };
    state.focusAnimationFrame = requestAnimationFrame(drawCanvas);
  }

  function stopFocusAnimation() {
    if (state.focusAnimationFrame) {
      cancelAnimationFrame(state.focusAnimationFrame);
      state.focusAnimationFrame = null;
    }
    state.focusAnimation = null;
  }

  function deriveAssetLabel(asset) {
    if (asset.display_label) return asset.display_label.substring(0, 3).toUpperCase();
    if (asset.asset?.name) return asset.asset.name.substring(0, 3).toUpperCase();
    return 'A';
  }

  function scheduleAutosave() {
    if (state.autosaveTimer) {
      clearTimeout(state.autosaveTimer);
    }
    state.autosaveTimer = setTimeout(executeAutosave, state.autosaveDelay);
    showStatus('Änderungen werden gespeichert...', 'info');
  }

  async function executeAutosave() {
    if (!state.currentRevision) return;

    const payload = {
      payload: {
        assets: state.assets.map((asset) => ({
          id: asset.id,
          position_x: Number(asset.position_x.toFixed(6)),
          position_y: Number(asset.position_y.toFixed(6)),
        })),
        timestamp: new Date().toISOString(),
      },
    };

    try {
      await fetch(`/api/floorplan-revisions/${state.currentRevision.id}/autosave`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.csrfToken || '',
        },
        body: JSON.stringify(payload),
      });
      showStatus('Auto-Save abgeschlossen.', 'success');
    } catch (err) {
      console.error('❌ ERROR: Autosave failed', err);
      showStatus('Auto-Save fehlgeschlagen.', 'error');
    }
  }

  async function handleSaveAssets() {
    if (!state.currentRevision) return;
    if (!state.assets || state.assets.length === 0) {
      showStatus('Keine Assets zum Speichern.', 'info');
      return;
    }

    state.isSaving = true;
    showStatus('Speichere Positionen...', 'info');

    try {
      await Promise.all(
        state.assets.map((asset) =>
          fetch(`/api/floorplan-assets/${asset.id}`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': window.csrfToken || '',
            },
            body: JSON.stringify({
              position_x: Number(asset.position_x.toFixed(4)),
              position_y: Number(asset.position_y.toFixed(4)),
            }),
          })
        )
      );

      showStatus('Änderungen gespeichert.', 'success');
    } catch (err) {
      console.error('❌ ERROR: Failed to save asset positions', err);
      showStatus('Fehler beim Speichern der Assets.', 'error');
    } finally {
      state.isSaving = false;
    }
  }

  function closeFloorplanPlanner() {
    state.modalEl.style.display = 'none';
    document.body.style.overflow = '';
    resetPlannerState();
  }

  function showStatus(message, type = 'info') {
    if (!state.statusEl) return;
    state.statusEl.textContent = message;
    state.statusEl.dataset.type = type;
  }

  function clearStatus() {
    if (!state.statusEl) return;
    state.statusEl.textContent = '';
    state.statusEl.dataset.type = '';
  }

  function updateScaleInfo() {
    if (!state.scaleInfoEl) return;
    const px = state.currentRevision?.scale_line_length_px;
    const cm = state.currentRevision?.scale_real_length_cm;

    if (!px || !cm) {
      state.scaleInfoEl.textContent = 'Maßstab nicht gesetzt';
      return;
    }

    const meters = cm / 100;
    const cmPerPixel = cm / px;
    const formattedMeters = meters >= 1 ? `${meters.toFixed(2)} m` : null;
    const parts = [`${cm.toFixed(1)} cm`, formattedMeters ? `(${formattedMeters})` : null, `für ${px.toFixed(1)} px`, `${cmPerPixel.toFixed(2)} cm/px`].filter(Boolean);
    state.scaleInfoEl.textContent = `Maßstab: ${parts.join(' · ')}`;
  }

  function drawScaleOverlay() {
    if (!state.canvasEl || !state.ctx) return;

    if (state.isSettingScale && state.scaleDraftPoints.length > 0) {
      const start = state.scaleDraftPoints[0];
      const end = state.scaleDraftPoints[1] || state.scaleHoverPoint;

      state.ctx.save();
      state.ctx.strokeStyle = '#ff9800';
      state.ctx.fillStyle = '#ff9800';
      state.ctx.lineWidth = 3;
      state.ctx.lineCap = 'round';

      state.ctx.beginPath();
      state.ctx.arc(start.x, start.y, 6, 0, Math.PI * 2);
      state.ctx.fill();

      if (end) {
        state.ctx.beginPath();
        state.ctx.moveTo(start.x, start.y);
        state.ctx.lineTo(end.x, end.y);
        state.ctx.stroke();

        state.ctx.beginPath();
        state.ctx.arc(end.x, end.y, 6, 0, Math.PI * 2);
        state.ctx.fill();

        const length = Math.hypot(end.x - start.x, end.y - start.y);
        const label = `${length.toFixed(0)} px`;
        state.ctx.font = 'bold 14px sans-serif';
        state.ctx.textAlign = 'center';
        state.ctx.textBaseline = 'bottom';
        state.ctx.fillText(label, (start.x + end.x) / 2, (start.y + end.y) / 2 - 8);
      }

      state.ctx.restore();
    }
  }

  // Expose globals
  window.openFloorplanPlannerFromEdit = openFloorplanPlannerFromEdit;
  window.openFloorplanPlanner = openFloorplanPlanner;
  window.closeFloorplanPlanner = closeFloorplanPlanner;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
