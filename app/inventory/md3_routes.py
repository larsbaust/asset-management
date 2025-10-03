# MD3 Inventory Routes - Migration from legacy inventory templates
# This module provides MD3-compliant routes for all inventory functionality

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import desc, asc, func
from sqlalchemy.orm import joinedload

from . import inventory_bp
from ..models import db, InventorySession, InventoryItem, Asset, Location, User, CostEntry

# ============================================================================
# INVENTUR PLANNING ROUTES (MD3)
# ============================================================================

@inventory_bp.route('/planning')
@login_required
def planning():
    """
    MD3 Inventurplanung - Hauptübersicht
    Migrated from: app/templates/inventory/planning.html
    """
    try:
        # Aktive und geplante Inventuren (matching original logic)
        active_sessions = InventorySession.query.options(
            joinedload(InventorySession.location),
            joinedload(InventorySession.created_by)
        ).filter(
            InventorySession.status.in_(['planned', 'in_progress', 'active'])
        ).order_by(InventorySession.start_date).all()
        
        # Abgeschlossene Inventuren
        completed_sessions = InventorySession.query.options(
            joinedload(InventorySession.location),
            joinedload(InventorySession.created_by)
        ).filter_by(
            status='completed'
        ).order_by(InventorySession.end_date.desc()).limit(5).all()
        
        # Alle Sessions für Statistiken
        all_sessions = active_sessions + completed_sessions
        
        # Calculate statistics for each session
        for session in all_sessions:
            session.total_items = InventoryItem.query.filter_by(session_id=session.id).count()
            session.completed_items = InventoryItem.query.filter_by(
                session_id=session.id, 
                status='completed'
            ).count()
            session.progress = (session.completed_items / session.total_items * 100) if session.total_items > 0 else 0
        
        # Get all locations for the dropdown (simplified approach)
        locations = Location.query.all()
        
        return render_template('md3/inventory/planning.html', 
                             sessions=all_sessions,
                             active_sessions=active_sessions,
                             completed_sessions=completed_sessions,
                             locations=locations,
                             page_title='Inventurplanung')
    
    except Exception as e:
        current_app.logger.error(f"Error in inventory planning: {str(e)}")
        flash('Fehler beim Laden der Inventurplanung', 'error')
        return redirect(url_for('main.dashboard'))

@inventory_bp.route('/planning/new', methods=['POST'])
@login_required
def planning_new():
    """
    MD3 Neue Inventur erstellen (POST only)
    Handles form submission from the integrated modal in planning.html
    """
    try:
        # Get form data
        name = request.form.get('name')
        notes = request.form.get('description', '')  # Modal uses 'description' but model uses 'notes'
        location_id = request.form.get('location_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        include_all_assets = request.form.get('include_all_assets') == 'on'
        
        # Validation
        if not name:
            flash('Name ist erforderlich', 'error')
            return redirect(url_for('inventory.planning'))
        
        # Parse dates - both are required for InventorySession
        if not start_date or not end_date:
            flash('Start- und Enddatum sind erforderlich', 'error')
            return redirect(url_for('inventory.planning'))
        
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            flash('Ungültiges Datum-Format', 'error')
            return redirect(url_for('inventory.planning'))
        
        # Validate date range
        if start_date_obj >= end_date_obj:
            flash('Enddatum muss nach dem Startdatum liegen', 'error')
            return redirect(url_for('md3_inventory.planning'))
        
        # Create new inventory session
        session = InventorySession(
            name=name,
            notes=notes,
            location_id=location_id if location_id and location_id != '' else None,
            start_date=start_date_obj,
            end_date=end_date_obj,
            status='planned',
            created_by_user_id=current_user.id
        )
        
        db.session.add(session)
        db.session.flush()  # Get the session ID
        
        # If include_all_assets is checked, create inventory items for all assets
        if include_all_assets:
            # Get assets based on location filter
            if session.location_id:
                assets = Asset.query.filter_by(location_id=session.location_id).all()
            else:
                assets = Asset.query.all()
            
            # Create inventory items
            for asset in assets:
                item = InventoryItem(
                    session_id=session.id,
                    asset_id=asset.id,
                    expected_quantity=1,  # Default quantity
                    expected_location=asset.location_obj.name if asset.location_obj else (asset.location if asset.location else 'Unbekannt'),
                    status='pending'
                )
                db.session.add(item)
        
        db.session.commit()
        
        # KALENDER-EVENT für Inventur erstellen
        from app.models import CalendarEvent, EVENT_TYPE_INVENTORY, EVENT_STATUS_PLANNED
        
        # Standort-Name für Beschreibung
        location_name = session.location.name if session.location else 'Kein Standort'
        event_title = f"Inventur: {session.name}"
        event_description = f"Inventur am Standort: {location_name}\nStatus: Geplant"
        
        if session.notes:
            event_description += f"\n\nNotizen:\n{session.notes}"
        
        calendar_event = CalendarEvent(
            title=event_title,
            description=event_description,
            start_datetime=session.start_date,
            end_datetime=session.end_date,
            event_type=EVENT_TYPE_INVENTORY,
            status=EVENT_STATUS_PLANNED,
            inventory_session_id=session.id,
            created_by_id=current_user.id
        )
        db.session.add(calendar_event)
        db.session.commit()
        current_app.logger.info(f"DEBUG: Kalender-Event #{calendar_event.id} für Inventurplanung #{session.id} erstellt")
        
        flash(f'Inventur "{name}" wurde erfolgreich erstellt', 'success')
        return redirect(url_for('md3_inventory.planning'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating inventory session: {str(e)}")
        flash('Fehler beim Erstellen der Inventur', 'error')
        return redirect(url_for('md3_inventory.planning'))

@inventory_bp.route('/planning/<int:id>', methods=['GET', 'POST'])
@login_required
def planning_detail(id):
    """
    MD3 Inventur Execution View - Load assets directly for counting
    """
    try:
        current_app.logger.info(f"Loading inventory session {id}")
        
        # Load session
        session = InventorySession.query.get_or_404(id)
        current_app.logger.info(f"Session loaded: {session.name}")
        
        # Note: Session status remains 'planned' until first progress is saved
        # This allows the Play-Button to remain visible until actual work begins
        
        # Load items for this inventory session based on InventoryItem entries ONLY.
        # Important: Do NOT filter by current Asset.location here, otherwise assets that moved
        # after session creation disappear from the UI but still count as uncounted on completion.
        session_items = (
            InventoryItem.query
            .filter_by(session_id=session.id)
            .options(joinedload(InventoryItem.asset))
            .all()
        )
        assets = [itm.asset for itm in session_items if itm.asset]
        if session.location_id:
            current_app.logger.info(f"Loading session-bound items (session is location-scoped: {session.location_id}) without filtering by current asset location")
        else:
            current_app.logger.info("Loading all session-bound items (no location filter)")
        
        current_app.logger.info(f"Found {len(assets)} session-bound assets for session {id}")
        
        # Load saved inventory item data for this session
        inventory_items = {}
        saved_items = InventoryItem.query.filter_by(session_id=session.id).all()
        for item in saved_items:
            # Extract damaged quantity from condition_notes
            damaged_qty = 0
            if item.condition_notes and 'damaged_qty:' in item.condition_notes:
                import re
                match = re.search(r'damaged_qty:(\d+)', item.condition_notes)
                if match:
                    damaged_qty = int(match.group(1))
            
            inventory_items[item.asset_id] = {
                'counted_quantity': item.counted_quantity,
                'damaged_quantity': damaged_qty,
                'actual_location': item.actual_location,
                'condition_notes': item.condition_notes,
                'condition': item.condition,
                'status': item.status,
                'counted_by': item.counted_by,
                'counted_at': item.counted_at
            }
        
        current_app.logger.info(f"Found {len(inventory_items)} saved inventory items for session {id}")
        
        # Calculate progress and status counts based on saved data (session items)
        # Use saved_items length to match completion validation (which checks all session items).
        total_assets = len(saved_items)
        counted_assets = len([item for item in saved_items if item.status == 'completed'])
        progress_percentage = 0 if total_assets == 0 else int((counted_assets / total_assets) * 100)
        
        # Calculate actual status counts from saved data
        gefunden = len([item for item in saved_items if item.counted_quantity is not None and item.counted_quantity > 0])
        fehlend = len([item for item in saved_items if item.counted_quantity == 0])
        beschaedigt = 0  # TODO: Implement damage logic based on condition
        unberuehrt = total_assets - len([item for item in saved_items if item.counted_quantity is not None])
        
        status_counts = {
            'gefunden': gefunden,
            'fehlend': fehlend,
            'beschaedigt': beschaedigt,
            'unberuehrt': unberuehrt
        }
        
        current_app.logger.info(f"Rendering execution template for session {id} with {total_assets} assets")
        return render_template('md3/inventory/execution.html', 
                             session=session,
                             assets=assets,
                             inventory_items=inventory_items,
                             total_assets=total_assets,
                             counted_assets=counted_assets,
                             progress_percentage=progress_percentage,
                             status_counts=status_counts)
    
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error loading inventory session {id}: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash('Fehler beim Laden der Inventur-Details', 'error')
        return redirect(url_for('inventory.planning'))

# ============================================================================
# INVENTUR EXECUTION ROUTES (MD3)
# ============================================================================

@inventory_bp.route('/execute')
@login_required
def execute():
    """
    MD3 Inventur durchführen - Übersicht
    Migrated from: app/templates/inventory/execute.html
    """
    try:
        # Get active inventory sessions (matching original logic)
        active_sessions = InventorySession.query.filter_by(status='active').all()
        
        # Add progress information
        for session in active_sessions:
            session.total_items = InventoryItem.query.filter_by(session_id=session.id).count()
            session.completed_items = InventoryItem.query.filter_by(
                session_id=session.id, 
                status='completed'
            ).count()
            session.progress = (session.completed_items / session.total_items * 100) if session.total_items > 0 else 0
        
        return render_template('md3/inventory/execute.html',
                             active_sessions=active_sessions,
                             sessions=active_sessions,  # For compatibility
                             page_title='Inventur durchführen')
    
    except Exception as e:
        current_app.logger.error(f"Error in inventory execution: {str(e)}")
        flash('Fehler beim Laden der Inventur-Durchführung', 'error')
        return redirect(url_for('main.dashboard'))

# ============================================================================
# INVENTUR REPORTS ROUTES (MD3)
# ============================================================================

@inventory_bp.route('/reports-legacy')
@login_required
def reports_legacy():
    """
    MD3 Inventurberichte - Übersicht
    Migrated from: app/templates/inventory/reports.html
    """
    try:
        # Get completed inventory sessions
        completed_sessions = (
            InventorySession.query.filter_by(status='completed')
            .options(
                joinedload(InventorySession.location_obj),
                joinedload(InventorySession.items)
            )
            .order_by(desc(InventorySession.end_date))
            .all()
        )

        # Minimal summaries placeholder to satisfy template
        session_summaries = {}
        
        return render_template(
            'md3/inventory/reports.html',
            completed_sessions=completed_sessions,
            session_summaries=session_summaries,
            page_title='Inventurberichte'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error in inventory reports: {str(e)}")
        flash('Fehler beim Laden der Inventurberichte', 'error')
        return redirect(url_for('main.dashboard'))

# ============================================================================
# INVENTUR HISTORY ROUTES (MD3)
# ============================================================================

@inventory_bp.route('/history')
@login_required
def history():
    """
    MD3 Inventurhistorie - Alle vergangenen Inventuren
    Migrated from: app/templates/inventory/history.html
    """
    try:
        # Get all inventory sessions
        all_sessions = InventorySession.query.options(
            joinedload(InventorySession.location_obj)
        ).order_by(desc(InventorySession.start_date)).all()
        
        # Add statistics for each session
        for session in all_sessions:
            session.total_items = InventoryItem.query.filter_by(session_id=session.id).count()
            session.completed_items = InventoryItem.query.filter_by(
                session_id=session.id, 
                status='completed'
            ).count()
        
        return render_template('md3/inventory/history.html',
                             sessions=all_sessions,
                             page_title='Inventurhistorie')
    
    except Exception as e:
        current_app.logger.error(f"Error in inventory history: {str(e)}")
        flash('Fehler beim Laden der Inventurhistorie', 'error')
        return redirect(url_for('main.dashboard'))

# ============================================================================
# API ENDPOINTS FOR MD3 INVENTORY
# ============================================================================

@inventory_bp.route('/api/start-session/<int:id>', methods=['POST'])
@login_required
def api_start_session(id):
    """Start an inventory session"""
    try:
        session = InventorySession.query.get_or_404(id)
        session.status = 'active'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Inventur gestartet'})
    except Exception as e:
        current_app.logger.error(f"Error starting session: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Starten der Inventur'})

@inventory_bp.route('/sessions/<int:session_id>/save-progress', methods=['POST'])
@login_required
def save_progress(session_id):
    """MD3 Fortschritt speichern - Saves inventory progress data"""
    try:
        current_app.logger.info(f"=== SAVE PROGRESS DEBUG START for session {session_id} ===")
        
        # Step 1: Get session
        current_app.logger.info(f"Step 1: Getting session {session_id}")
        session = InventorySession.query.get_or_404(session_id)
        current_app.logger.info(f"Session found: {session.name}, status: {session.status}")
        
        # Step 2: Get data (JSON or Form)
        current_app.logger.info(f"Step 2: Getting data - Content-Type: {request.content_type}")
        
        # Try JSON first, then fallback to form data
        data = request.get_json()
        if data:
            current_app.logger.info(f"Received JSON data: {data}")
        else:
            # Process form data - convert to asset dict format
            current_app.logger.info(f"No JSON data, processing form data...")
            data = {}
            for key, value in request.form.items():
                if key.startswith('counted_quantity_'):
                    asset_id = key.replace('counted_quantity_', '')
                    try:
                        asset_id = int(asset_id)
                        counted_qty = int(value) if value.isdigit() else 0
                        data[str(asset_id)] = {
                            'counted_quantity': counted_qty,
                            'status': 'completed' if counted_qty > 0 else 'pending'
                        }
                    except (ValueError, TypeError):
                        continue
            current_app.logger.info(f"Converted form data: {data}")
        
        if not data:
            current_app.logger.error("No data received")
            return jsonify({'success': False, 'message': 'Keine Daten empfangen'})
        
        # Step 3: Process each asset
        current_app.logger.info(f"Step 3: Processing {len(data)} assets")
        for asset_id, asset_data in data.items():
            try:
                current_app.logger.info(f"Processing asset_id: {asset_id}, data: {asset_data}")
                asset_id = int(asset_id)
                
                # Find inventory item
                item = InventoryItem.query.filter_by(
                    session_id=session.id, 
                    asset_id=asset_id
                ).first()
                
                if not item:
                    current_app.logger.warning(f"No inventory item found for asset_id {asset_id} in session {session_id}")
                    continue
                
                current_app.logger.info(f"Found inventory item: {item.id}")
                
                # Update fields safely
                if 'counted_quantity' in asset_data:
                    old_qty = item.counted_quantity
                    item.counted_quantity = asset_data['counted_quantity']
                    current_app.logger.info(f"Updated counted_quantity: {old_qty} -> {item.counted_quantity}")
                
                if 'actual_location' in asset_data:
                    old_location = item.actual_location
                    item.actual_location = asset_data['actual_location']
                    current_app.logger.info(f"Updated actual_location: {old_location} -> {item.actual_location}")
                
                if 'notes' in asset_data:
                    old_notes = item.condition_notes
                    item.condition_notes = asset_data['notes']
                    current_app.logger.info(f"Updated condition_notes: {old_notes} -> {item.condition_notes}")
                
                # Set status and metadata
                if 'counted_quantity' in asset_data and asset_data['counted_quantity'] is not None:
                    counted_qty = int(asset_data.get('counted_quantity', 0))
                    old_status = item.status
                    # Any provided quantity (including 0) means the item has been counted
                    item.status = 'completed'
                    current_app.logger.info(f"Updated status: {old_status} -> {item.status} (counted_qty={counted_qty})")
                
                # Set metadata
                item.counted_by = current_user.username if current_user.is_authenticated else 'System'
                item.counted_at = datetime.utcnow()
                current_app.logger.info(f"Set counted_by: {item.counted_by}, counted_at: {item.counted_at}")
                    
            except (ValueError, KeyError) as e:
                current_app.logger.error(f"Error processing asset {asset_id}: {str(e)}")
                continue
            except Exception as e:
                current_app.logger.error(f"Unexpected error processing asset {asset_id}: {str(e)}")
                continue
        
        # Step 4: Update session status
        current_app.logger.info(f"Step 4: Updating session status")
        if session.status == 'planned':
            old_status = session.status
            session.status = 'active'
            current_app.logger.info(f"Session status updated: {old_status} -> {session.status}")
        
        # Step 5: Commit to database
        current_app.logger.info(f"Step 5: Committing to database")
        db.session.commit()
        current_app.logger.info(f"Database commit successful")
        
        current_app.logger.info(f"=== SAVE PROGRESS DEBUG SUCCESS ===")
        
        return jsonify({
            'success': True, 
            'message': 'Fortschritt erfolgreich gespeichert',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"=== SAVE PROGRESS DEBUG ERROR ===")
        current_app.logger.error(f"Exception type: {type(e).__name__}")
        current_app.logger.error(f"Exception message: {str(e)}")
        current_app.logger.error(f"Exception args: {e.args}")
        import traceback
        current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
        current_app.logger.error(f"=== SAVE PROGRESS DEBUG ERROR END ===")
        
        return jsonify({
            'success': False, 
            'message': f'Fehler beim Speichern des Fortschritts: {str(e)}'
        })

@inventory_bp.route('/sessions/<int:session_id>/complete', methods=['POST'])
@login_required
def complete_inventory(session_id):
    """MD3 Inventur abschließen - Complete inventory and generate report"""
    try:
        session = InventorySession.query.get_or_404(session_id)
        
        # Check if all items have been counted (NULL values only, 0 is valid for missing assets)
        # IMPORTANT: Exclude orphaned items (where related Asset no longer exists),
        # because they cannot be shown/edited in the UI and should not block completion.
        from sqlalchemy.orm import aliased
        uncounted_items_query = (
            InventoryItem.query
            .filter(InventoryItem.session_id == session.id)
            .join(Asset, InventoryItem.asset_id == Asset.id, isouter=True)
            .filter(
                InventoryItem.counted_quantity.is_(None),
                Asset.id.isnot(None)
            )
        )
        uncounted_count = uncounted_items_query.count()
        current_app.logger.info(f"Completion check: session_items={len(session.items)}, uncounted_visible_items={uncounted_count}")
        
        if uncounted_count > 0:
            # Get details about uncounted items for better user feedback
            uncounted_items = uncounted_items_query.limit(10).all()
            uncounted_names = [f"• {item.asset.name}" for item in uncounted_items if item.asset]
            
            if uncounted_count > 10:
                uncounted_names.append(f"• ... und {uncounted_count - 10} weitere")
            
            uncounted_list = "\n".join(uncounted_names) if uncounted_names else ""
            
            return jsonify({
                'success': False, 
                'message': f'Es gibt noch {uncounted_count} ungezählte Assets in dieser Inventur.\n\nBeispiele ungezählter Assets:\n{uncounted_list}\n\nBitte geben Sie für alle Assets eine Menge ein (auch "0" für fehlende Assets), bevor Sie die Inventur abschließen.',
                'uncounted_count': uncounted_count,
                'uncounted_examples': uncounted_names[:10]
            })
        
        # Set status for all items based on counting results
        for item in session.items:
            if item.counted_quantity is not None:
                # Check for damaged condition
                if item.condition and item.condition in ['damaged', 'repair_needed']:
                    item.status = 'damaged'
                elif item.counted_quantity > 0:
                    item.status = 'found'
                else:
                    item.status = 'missing'
            else:
                item.status = 'missing'
            
            # Location check
            if item.actual_location and item.expected_location:
                item.location_correct = (item.actual_location.strip().lower() == item.expected_location.strip().lower())
        
        # Complete the session
        session.status = 'completed'
        session.end_date = datetime.utcnow()
        
        # Add completion metadata
        if hasattr(session, 'completed_by'):
            session.completed_by = current_user.username if current_user.is_authenticated else 'System'
        if hasattr(session, 'completed_at'):
            session.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        current_app.logger.info(f"Inventory session {session_id} completed by {current_user.username if current_user.is_authenticated else 'System'}")
        
        return jsonify({
            'success': True, 
            'message': 'Inventur wurde erfolgreich abgeschlossen!',
            'redirect_url': url_for('md3_inventory.md3_reports')
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing inventory session {session_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Abschließen der Inventur'})

@inventory_bp.route('/api/complete-session/<int:id>', methods=['POST'])
@login_required
def api_complete_session(id):
    """Legacy API endpoint - redirects to new complete endpoint"""
    return complete_inventory(id)

# ============================================================================
# INVENTUR REPORTS ROUTES (MD3)
# ============================================================================

@inventory_bp.route('/test')
def test_route():
    """Test route to verify MD3 inventory blueprint is working"""
    return "<h1>MD3 Inventory Blueprint Works!</h1><p>Route: /md3/inventory/test</p>"

@inventory_bp.route('/reports')
@login_required
def md3_reports():
    """
    MD3 Inventurberichte - Übersicht aller abgeschlossenen Inventuren
    SIMPLIFIED VERSION to bypass created_by AttributeError
    """
    current_app.logger.info("=== MD3 REPORTS DEBUG START ===")
    try:
        current_app.logger.info("Step 1: Getting completed sessions")
        
        # Get completed sessions with minimal query
        # Include sessions where either status='completed' OR completed_at is set
        from sqlalchemy import or_
        completed_sessions = (
            InventorySession.query
            .filter(
                or_(
                    InventorySession.status == 'completed',
                    InventorySession.completed_at.isnot(None)
                )
            )
            .order_by(InventorySession.end_date.desc())
            .all()
        )
        current_app.logger.info(f"Found {len(completed_sessions)} completed sessions (status=completed or completed_at not null)")
        
        # Additional diagnostics
        total_sessions_count = InventorySession.query.count()
        recent_sessions = (
            InventorySession.query.order_by(InventorySession.id.desc()).limit(5).all()
        )
        recent_sessions_info = [
            {
                'id': s.id,
                'name': s.name,
                'status': s.status,
                'completed_at': s.completed_at.isoformat() if getattr(s, 'completed_at', None) else None,
                'end_date': s.end_date.isoformat() if getattr(s, 'end_date', None) else None,
            }
            for s in recent_sessions
        ]
        current_app.logger.info(f"Total sessions in DB: {total_sessions_count}")
        current_app.logger.info(f"Recent sessions: {recent_sessions_info}")

        # Build per-session summaries for charts
        session_summaries = {}
        for session in completed_sessions:
            current_app.logger.info(f"Processing session {session.id}: {session.name}")
            
            # Load items for this session
            items = InventoryItem.query.filter_by(session_id=session.id).all()
            found = 0
            missing = 0
            damaged = 0
            
            for itm in items:
                # Partition into mutually exclusive buckets
                if getattr(itm, 'condition', None) in ('damaged', 'repair_needed'):
                    damaged += 1
                elif itm.counted_quantity and itm.counted_quantity > 0:
                    found += 1
                else:
                    missing += 1
            
            total = found + missing + damaged
            session_summaries[session.id] = {
                'found': found,
                'missing': missing,
                'damaged': damaged,
                'total': total
            }
        
        current_app.logger.info("Step 2: Rendering template")
        current_app.logger.info(f"Sessions to render: {[s.id for s in completed_sessions]}")
        
        return render_template('md3/inventory/reports.html',
                             completed_sessions=completed_sessions,
                             sessions_list=completed_sessions,
                             session_summaries=session_summaries,
                             total_sessions_count=total_sessions_count,
                             recent_sessions_info=recent_sessions_info)
        
    except Exception as e:
        current_app.logger.error(f"=== MD3 REPORTS ERROR ===")
        current_app.logger.error(f"Exception type: {type(e).__name__}")
        current_app.logger.error(f"Exception message: {str(e)}")
        import traceback
        current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
        current_app.logger.error(f"=== MD3 REPORTS ERROR END ===")
        
        # Return simple HTML instead of redirect to see the error
        return f"""
        <h1>MD3 Reports Debug Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p><strong>Type:</strong> {type(e).__name__}</p>
        <pre>{traceback.format_exc()}</pre>
        <a href="/md3/dashboard">Zurück zum Dashboard</a>
        """

@inventory_bp.route('/reports/<int:id>')
@login_required
def md3_report_detail(id):
    """
    MD3 Inventurbericht Detail - Detailansicht eines spezifischen Berichts
    Migrated from: app/main.py inventory_report_detail() function
    """
    try:
        # Load session with all related data
        from sqlalchemy import or_
        session = (
            InventorySession.query
            .options(
                joinedload(InventorySession.items).joinedload(InventoryItem.asset),
                joinedload(InventorySession.location_obj)
            )
            .filter(
                InventorySession.id == id,
                or_(
                    InventorySession.status == 'completed',
                    InventorySession.completed_at.isnot(None)
                )
            )
            .first_or_404()
        )
        
        # Prepare chart data (matching original logic)
        chart_data = prepare_chart_data(session)
        
        # Prepare asset list for JavaScript
        asset_list = []
        for item in session.items:
            # Guard against missing asset relation
            if not item.asset:
                continue
            asset_list.append({
                'item': {
                    'id': item.id,
                    'expected_quantity': item.expected_quantity,
                    'counted_quantity': item.counted_quantity,
                    'expected_location': item.expected_location,
                    'actual_location': item.actual_location,
                    'condition': item.condition,
                    'condition_notes': item.condition_notes,
                    'status': item.status,
                    'asset': {
                        'id': item.asset.id,
                        'name': item.asset.name,
                        'article_number': item.asset.article_number,
                        'serial_number': item.asset.serial_number,
                        'location': ({
                            'name': item.asset.location_obj.name
                        } if item.asset.location_obj else None)
                    }
                }
            })
        
        return render_template('md3/inventory/report_detail.html',
                             session=session,
                             chart_data=chart_data,
                             asset_list=asset_list)
        
    except Exception as e:
        current_app.logger.error(f"Error loading inventory report detail {id}: {str(e)}")
        flash('Fehler beim Laden des Inventurberichts', 'error')
        return redirect(url_for('md3_inventory.md3_reports'))

def prepare_chart_data(session):
    """
    Prepare chart data for the report detail view
    Matches the original logic from main.py
    """
    # Status distribution (derived)
    found_count = 0
    missing_count = 0
    damaged_count = 0
    
    # Category distribution
    category_data = {}
    
    # Location distribution
    location_data = {}
    
    # Timeline data (simplified - could be enhanced)
    timeline_labels = []
    timeline_data = []
    
    for item in session.items:
        # Derive found/missing from counted quantities
        if item.counted_quantity is not None:
            if item.counted_quantity > 0:
                found_count += 1
            elif item.counted_quantity == 0:
                missing_count += 1
        else:
            # Treat None as missing for completed sessions fallback
            missing_count += 1
        
        # Derive damaged from condition
        if getattr(item, 'condition', None) in ('damaged', 'repair_needed'):
            damaged_count += 1
        
        # Category distribution
        category = item.asset.category.name if hasattr(item.asset, 'category') and item.asset.category else 'Unbekannt'
        if category not in category_data:
            category_data[category] = 0
        category_data[category] += item.counted_quantity or 0
        
        # Location distribution
        location = item.actual_location or item.expected_location or 'Unbekannt'
        if location not in location_data:
            location_data[location] = 0
        location_data[location] += item.counted_quantity or 0
    
    return {
        'status': {
            'labels': ['Gefunden', 'Fehlend', 'Beschädigt'],
            'data': [found_count, missing_count, damaged_count]
        },
        'category': {
            'labels': list(category_data.keys()),
            'data': list(category_data.values())
        },
        'location': {
            'labels': list(location_data.keys()),
            'data': list(location_data.values())
        },
        'timeline': {
            'labels': timeline_labels,
            'data': timeline_data
        }
    }

@inventory_bp.route('/api/start/<int:session_id>', methods=['POST'])
@login_required
def api_start_inventory(session_id):
    """API endpoint to start inventory session"""
    try:
        session = InventorySession.query.get_or_404(session_id)
        session.status = 'active'
        session.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Inventur gestartet'})
    except Exception as e:
        current_app.logger.error(f"Error starting inventory session {session_id}: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Starten der Inventur'}), 500

@inventory_bp.route('/api/complete/<int:session_id>', methods=['POST'])
@login_required  
def api_complete_inventory(session_id):
    """API endpoint to complete inventory session"""
    try:
        session = InventorySession.query.get_or_404(session_id)
        session.status = 'completed'
        session.completed_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Inventur abgeschlossen'})
    except Exception as e:
        current_app.logger.error(f"Error completing inventory session {session_id}: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Abschließen der Inventur'}), 500

