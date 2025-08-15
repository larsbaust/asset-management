// MD3 Inventory Report Detail Asset Management
// Enhanced version of the original report_detail_asset.js with MD3 styling and interactions

document.addEventListener('DOMContentLoaded', function() {
    // Initialize asset table functionality
    initializeAssetTable();
    
    // Initialize export functionality
    initializeExportFunctions();
    
    // Initialize search and filter functionality
    initializeSearchAndFilter();
});

/**
 * Initialize the asset table with grouping and detail expansion
 */
function initializeAssetTable() {
    const assetData = getAssetData();
    if (!assetData || assetData.length === 0) {
        showEmptyState();
        return;
    }
    
    // Group assets by name and article number
    const groupedAssets = groupAssetsByType(assetData);
    
    // Render the grouped table
    renderGroupedTable(groupedAssets);
    
    // Initialize table interactions
    initializeTableInteractions();
}

/**
 * Get asset data from the hidden script tag
 */
function getAssetData() {
    try {
        const dataElement = document.getElementById('assetData');
        if (dataElement) {
            return JSON.parse(dataElement.textContent);
        }
        return [];
    } catch (error) {
        console.error('Error parsing asset data:', error);
        return [];
    }
}

/**
 * Group assets by type (name + article number)
 */
function groupAssetsByType(assetData) {
    const groups = {};
    
    assetData.forEach(asset => {
        const key = `${asset.item.asset.name}_${asset.item.asset.article_number || 'no-article'}`;
        
        if (!groups[key]) {
            groups[key] = {
                name: asset.item.asset.name,
                article_number: asset.item.asset.article_number || '-',
                expected_total: 0,
                counted_total: 0,
                items: [],
                locations: new Set(),
                conditions: new Set(),
                has_discrepancy: false,
                has_damage: false
            };
        }
        
        const group = groups[key];
        group.expected_total += asset.item.expected_quantity || 0;
        group.counted_total += asset.item.counted_quantity || 0;
        group.items.push(asset);
        
        // Collect locations
        if (asset.item.actual_location) {
            group.locations.add(asset.item.actual_location);
        } else if (asset.item.expected_location) {
            group.locations.add(asset.item.expected_location);
        }
        
        // Collect conditions
        if (asset.item.condition) {
            group.conditions.add(asset.item.condition);
            if (asset.item.condition === 'damaged' || asset.item.condition === 'repair_needed') {
                group.has_damage = true;
            }
        }
        
        // Check for discrepancies
        if (Math.abs((asset.item.expected_quantity || 0) - (asset.item.counted_quantity || 0)) > 0) {
            group.has_discrepancy = true;
        }
    });
    
    return groups;
}

/**
 * Render the grouped table
 */
function renderGroupedTable(groupedAssets) {
    const tbody = document.getElementById('assetTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    Object.entries(groupedAssets).forEach(([key, group]) => {
        // Create group row
        const groupRow = createGroupRow(key, group);
        tbody.appendChild(groupRow);
        
        // Create detail row (initially hidden)
        const detailRow = createDetailRow(key, group);
        tbody.appendChild(detailRow);
    });
}

/**
 * Create a group row for the table
 */
function createGroupRow(key, group) {
    const row = document.createElement('tr');
    row.className = 'md3-table-row group-row';
    row.dataset.groupKey = key;
    
    const discrepancy = Math.abs(group.expected_total - group.counted_total);
    const statusClass = getStatusClass(group);
    const statusText = getStatusText(group);
    
    row.innerHTML = `
        <td class="md3-table-cell">
            <button class="md3-icon-button toggle-details" data-group="${key}" title="Details anzeigen">
                <span class="material-symbols-outlined">expand_more</span>
            </button>
        </td>
        <td class="md3-table-cell">
            <div class="md3-asset-name">
                <span class="md3-asset-title">${escapeHtml(group.name)}</span>
                ${group.has_damage ? '<span class="md3-damage-indicator" title="Beschädigte Assets vorhanden"><span class="material-symbols-outlined">warning</span></span>' : ''}
            </div>
        </td>
        <td class="md3-table-cell">${escapeHtml(group.article_number)}</td>
        <td class="md3-table-cell">
            <span class="md3-quantity-badge">${group.expected_total}</span>
        </td>
        <td class="md3-table-cell">
            <span class="md3-quantity-badge ${group.counted_total !== group.expected_total ? 'md3-quantity-discrepancy' : ''}">${group.counted_total}</span>
        </td>
        <td class="md3-table-cell">
            <span class="md3-chip ${discrepancy > 0 ? 'md3-chip-error' : 'md3-chip-success'}">
                ${discrepancy > 0 ? `±${discrepancy}` : '0'}
            </span>
        </td>
        <td class="md3-table-cell">
            <span class="md3-chip ${statusClass}">
                ${statusText}
            </span>
        </td>
        <td class="md3-table-cell">
            <div class="md3-locations">
                ${Array.from(group.locations).slice(0, 2).map(loc => 
                    `<span class="md3-location-chip">${escapeHtml(loc)}</span>`
                ).join('')}
                ${group.locations.size > 2 ? `<span class="md3-location-more">+${group.locations.size - 2}</span>` : ''}
            </div>
        </td>
    `;
    
    return row;
}

/**
 * Create a detail row for expanded view
 */
function createDetailRow(key, group) {
    const row = document.createElement('tr');
    row.className = 'md3-table-detail-row';
    row.dataset.groupKey = key;
    row.style.display = 'none';
    
    row.innerHTML = `
        <td colspan="8" class="md3-table-detail-cell">
            <div class="md3-detail-container" id="detail-${key}">
                <div class="md3-detail-loading">
                    <span class="md3-loading-spinner"></span>
                    <span>Details werden geladen...</span>
                </div>
            </div>
        </td>
    `;
    
    return row;
}

/**
 * Initialize table interactions (expand/collapse, etc.)
 */
function initializeTableInteractions() {
    // Add event listeners for expand/collapse buttons
    document.querySelectorAll('.toggle-details').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const groupKey = this.dataset.group;
            toggleGroupDetails(groupKey, this);
        });
    });
    
    // Add row click handlers for better UX
    document.querySelectorAll('.group-row').forEach(row => {
        row.addEventListener('click', function(e) {
            // Don't trigger if clicking on the button
            if (e.target.closest('.toggle-details')) return;
            
            const button = this.querySelector('.toggle-details');
            if (button) {
                button.click();
            }
        });
        
        // Add hover effects
        row.addEventListener('mouseenter', function() {
            this.classList.add('md3-table-row-hover');
        });
        
        row.addEventListener('mouseleave', function() {
            this.classList.remove('md3-table-row-hover');
        });
    });
}

/**
 * Toggle group details expansion
 */
function toggleGroupDetails(groupKey, button) {
    const detailRow = document.querySelector(`.md3-table-detail-row[data-group-key="${groupKey}"]`);
    const icon = button.querySelector('.material-symbols-outlined');
    
    if (!detailRow) return;
    
    if (detailRow.style.display === 'none') {
        // Expand
        detailRow.style.display = 'table-row';
        icon.textContent = 'expand_less';
        button.setAttribute('title', 'Details ausblenden');
        
        // Load details if not already loaded
        const detailContainer = document.getElementById(`detail-${groupKey}`);
        if (detailContainer && detailContainer.querySelector('.md3-detail-loading')) {
            loadGroupDetails(groupKey, detailContainer);
        }
        
        // Smooth scroll to make sure the details are visible
        setTimeout(() => {
            detailRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
        
    } else {
        // Collapse
        detailRow.style.display = 'none';
        icon.textContent = 'expand_more';
        button.setAttribute('title', 'Details anzeigen');
    }
}

/**
 * Load and render group details
 */
function loadGroupDetails(groupKey, container) {
    const assetData = getAssetData();
    const [name, articleNumber] = groupKey.split('_');
    
    // Find items for this group
    const groupItems = assetData.filter(asset => 
        asset.item.asset.name === name && 
        (asset.item.asset.article_number || 'no-article') === articleNumber
    );
    
    if (groupItems.length === 0) {
        container.innerHTML = '<div class="md3-detail-empty">Keine Details verfügbar</div>';
        return;
    }
    
    // Create detailed table
    const detailTable = createDetailTable(groupItems);
    container.innerHTML = '';
    container.appendChild(detailTable);
}

/**
 * Create detailed table for individual assets
 */
function createDetailTable(items) {
    const table = document.createElement('table');
    table.className = 'md3-detail-table';
    
    // Create header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Seriennummer</th>
            <th>Erwartet</th>
            <th>Gezählt</th>
            <th>Erwarteter Standort</th>
            <th>Tatsächlicher Standort</th>
            <th>Zustand</th>
            <th>Notizen</th>
            <th>Status</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Create body
    const tbody = document.createElement('tbody');
    items.forEach(asset => {
        const row = document.createElement('tr');
        row.className = 'md3-detail-row';
        
        const expectedQty = asset.item.expected_quantity || 0;
        const countedQty = asset.item.counted_quantity || 0;
        const hasDiscrepancy = expectedQty !== countedQty;
        
        row.innerHTML = `
            <td>${escapeHtml(asset.item.asset.serial_number || '-')}</td>
            <td><span class="md3-quantity-badge">${expectedQty}</span></td>
            <td><span class="md3-quantity-badge ${hasDiscrepancy ? 'md3-quantity-discrepancy' : ''}">${countedQty}</span></td>
            <td>${escapeHtml(asset.item.expected_location || '-')}</td>
            <td>${escapeHtml(asset.item.actual_location || '-')}</td>
            <td>
                <span class="md3-chip ${getConditionClass(asset.item.condition)}">
                    ${escapeHtml(asset.item.condition || 'OK')}
                </span>
            </td>
            <td class="md3-notes-cell">${escapeHtml(asset.item.condition_notes || '-')}</td>
            <td>
                <span class="md3-chip ${getItemStatusClass(asset.item)}">
                    ${getItemStatusText(asset.item)}
                </span>
            </td>
        `;
        
        tbody.appendChild(row);
    });
    table.appendChild(tbody);
    
    return table;
}

/**
 * Initialize export functionality
 */
function initializeExportFunctions() {
    // Export asset table to CSV
    window.exportAssetTable = function() {
        const assetData = getAssetData();
        if (!assetData || assetData.length === 0) {
            showNotification('Keine Daten zum Exportieren verfügbar', 'warning');
            return;
        }
        
        const csv = generateCSV(assetData);
        downloadCSV(csv, 'inventur_assets.csv');
        showNotification('Asset-Tabelle erfolgreich exportiert', 'success');
    };
    
    // Download report as PDF (placeholder)
    window.downloadReport = function() {
        showNotification('PDF-Export wird implementiert...', 'info');
        // TODO: Implement PDF generation
    };
}

/**
 * Generate CSV from asset data
 */
function generateCSV(assetData) {
    const headers = [
        'Asset Name',
        'Artikelnummer',
        'Seriennummer',
        'Erwartet',
        'Gezählt',
        'Erwarteter Standort',
        'Tatsächlicher Standort',
        'Zustand',
        'Notizen',
        'Status'
    ];
    
    const rows = assetData.map(asset => [
        asset.item.asset.name,
        asset.item.asset.article_number || '',
        asset.item.asset.serial_number || '',
        asset.item.expected_quantity || 0,
        asset.item.counted_quantity || 0,
        asset.item.expected_location || '',
        asset.item.actual_location || '',
        asset.item.condition || '',
        asset.item.condition_notes || '',
        asset.item.status || ''
    ]);
    
    const csvContent = [headers, ...rows]
        .map(row => row.map(field => `"${String(field).replace(/"/g, '""')}"`).join(','))
        .join('\n');
    
    return csvContent;
}

/**
 * Download CSV file
 */
function downloadCSV(csvContent, filename) {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

/**
 * Initialize search and filter functionality
 */
function initializeSearchAndFilter() {
    // Add search functionality if search input exists
    const searchInput = document.getElementById('assetSearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(handleSearch, 300));
    }
    
    // Add filter functionality
    const filterButtons = document.querySelectorAll('.md3-filter-button');
    filterButtons.forEach(button => {
        button.addEventListener('click', handleFilter);
    });
}

/**
 * Handle search functionality
 */
function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();
    const rows = document.querySelectorAll('.group-row');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const shouldShow = text.includes(searchTerm);
        
        row.style.display = shouldShow ? '' : 'none';
        
        // Also hide/show corresponding detail row
        const detailRow = row.nextElementSibling;
        if (detailRow && detailRow.classList.contains('md3-table-detail-row')) {
            detailRow.style.display = shouldShow ? detailRow.style.display : 'none';
        }
    });
}

/**
 * Handle filter functionality
 */
function handleFilter(event) {
    const filterType = event.target.dataset.filter;
    const rows = document.querySelectorAll('.group-row');
    
    // Remove active state from all filter buttons
    document.querySelectorAll('.md3-filter-button').forEach(btn => {
        btn.classList.remove('md3-filter-active');
    });
    
    // Add active state to clicked button
    event.target.classList.add('md3-filter-active');
    
    rows.forEach(row => {
        let shouldShow = true;
        
        switch (filterType) {
            case 'all':
                shouldShow = true;
                break;
            case 'discrepancies':
                shouldShow = row.querySelector('.md3-chip-error') !== null;
                break;
            case 'damaged':
                shouldShow = row.querySelector('.md3-damage-indicator') !== null;
                break;
            case 'complete':
                shouldShow = row.querySelector('.md3-chip-success') !== null;
                break;
        }
        
        row.style.display = shouldShow ? '' : 'none';
        
        // Also hide/show corresponding detail row
        const detailRow = row.nextElementSibling;
        if (detailRow && detailRow.classList.contains('md3-table-detail-row')) {
            detailRow.style.display = shouldShow ? detailRow.style.display : 'none';
        }
    });
}

/**
 * Utility functions
 */

function getStatusClass(group) {
    if (group.has_damage) return 'md3-chip-error';
    if (group.has_discrepancy) return 'md3-chip-warning';
    return 'md3-chip-success';
}

function getStatusText(group) {
    if (group.has_damage) return 'Beschädigt';
    if (group.has_discrepancy) return 'Abweichung';
    return 'OK';
}

function getConditionClass(condition) {
    switch (condition) {
        case 'damaged':
        case 'repair_needed':
            return 'md3-chip-error';
        case 'good':
        case 'excellent':
            return 'md3-chip-success';
        case 'fair':
            return 'md3-chip-warning';
        default:
            return 'md3-chip-neutral';
    }
}

function getItemStatusClass(item) {
    const expectedQty = item.expected_quantity || 0;
    const countedQty = item.counted_quantity || 0;
    
    if (item.condition === 'damaged' || item.condition === 'repair_needed') {
        return 'md3-chip-error';
    }
    
    if (expectedQty !== countedQty) {
        return 'md3-chip-warning';
    }
    
    return 'md3-chip-success';
}

function getItemStatusText(item) {
    const expectedQty = item.expected_quantity || 0;
    const countedQty = item.counted_quantity || 0;
    
    if (item.condition === 'damaged' || item.condition === 'repair_needed') {
        return 'Beschädigt';
    }
    
    if (expectedQty !== countedQty) {
        return 'Abweichung';
    }
    
    return 'OK';
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `md3-notification md3-notification-${type}`;
    notification.innerHTML = `
        <span class="material-symbols-outlined">${getNotificationIcon(type)}</span>
        <span>${escapeHtml(message)}</span>
        <button class="md3-notification-close" onclick="this.parentElement.remove()">
            <span class="material-symbols-outlined">close</span>
        </button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function getNotificationIcon(type) {
    switch (type) {
        case 'success': return 'check_circle';
        case 'warning': return 'warning';
        case 'error': return 'error';
        default: return 'info';
    }
}

function showEmptyState() {
    const tbody = document.getElementById('assetTableBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="md3-empty-state-cell">
                    <div class="md3-empty-state">
                        <span class="material-symbols-outlined">inventory_2</span>
                        <h3>Keine Assets gefunden</h3>
                        <p>Für diese Inventur sind keine Asset-Daten verfügbar.</p>
                    </div>
                </td>
            </tr>
        `;
    }
}
