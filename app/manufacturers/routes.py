# MD3 Manufacturers Routes - Modern manufacturer management interface
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import desc, func

from . import manufacturers_bp
from ..models import db, Manufacturer, Asset

@manufacturers_bp.route('/')
@login_required
def manufacturers():
    """MD3 Manufacturers list view"""
    try:
        # Get all manufacturers (simplified query - no complex JOIN for now)
        manufacturers_data = Manufacturer.query.order_by(Manufacturer.name.asc()).all()
        
        # Convert to list of dicts for template
        manufacturers_list = []
        for manufacturer in manufacturers_data:
            # Count assets for this manufacturer manually
            asset_count = len(manufacturer.assets) if hasattr(manufacturer, 'assets') else 0
            
            manufacturers_list.append({
                'id': manufacturer.id,
                'name': manufacturer.name,
                'description': manufacturer.description,
                'website': manufacturer.website,
                'contact_info': manufacturer.contact_info,
                'created_at': manufacturer.created_at,
                'updated_at': manufacturer.updated_at,
                'asset_count': asset_count
            })
        
        return render_template('md3/manufacturers/manufacturers.html', 
                             manufacturers=manufacturers_list,
                             total_manufacturers=len(manufacturers_list))
                             
    except Exception as e:
        current_app.logger.error(f"Error loading manufacturers: {e}")
        flash('Fehler beim Laden der Hersteller', 'error')
        return render_template('md3/manufacturers/manufacturers.html', 
                             manufacturers=[],
                             total_manufacturers=0)

@manufacturers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_manufacturer():
    """Add new manufacturer"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            website = request.form.get('website', '').strip()
            contact_info = request.form.get('contact_info', '').strip()
            
            if not name:
                return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
            
            # Check if manufacturer already exists
            existing_manufacturer = Manufacturer.query.filter_by(name=name).first()
            if existing_manufacturer:
                return jsonify({'success': False, 'message': 'Hersteller mit diesem Namen existiert bereits'}), 400
            
            # Create new manufacturer
            new_manufacturer = Manufacturer(
                name=name,
                description=description,
                website=website,
                contact_info=contact_info,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_manufacturer)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Hersteller erfolgreich erstellt',
                'manufacturer': {
                    'id': new_manufacturer.id,
                    'name': new_manufacturer.name,
                    'description': new_manufacturer.description,
                    'website': new_manufacturer.website,
                    'contact_info': new_manufacturer.contact_info,
                    'asset_count': 0
                }
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating manufacturer: {e}")
            return jsonify({'success': False, 'message': 'Fehler beim Erstellen des Herstellers'}), 500
    
    # GET request - return to manufacturers list (modal handles form)
    return redirect(url_for('md3_manufacturers.manufacturers'))

@manufacturers_bp.route('/edit/<int:manufacturer_id>', methods=['GET', 'POST'])
@login_required
def edit_manufacturer(manufacturer_id):
    """Edit existing manufacturer"""
    manufacturer = Manufacturer.query.get_or_404(manufacturer_id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            website = request.form.get('website', '').strip()
            contact_info = request.form.get('contact_info', '').strip()
            
            if not name:
                return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
            
            # Check if another manufacturer has this name
            existing_manufacturer = Manufacturer.query.filter(
                Manufacturer.name == name,
                Manufacturer.id != manufacturer_id
            ).first()
            
            if existing_manufacturer:
                return jsonify({'success': False, 'message': 'Hersteller mit diesem Namen existiert bereits'}), 400
            
            # Update manufacturer
            manufacturer.name = name
            manufacturer.description = description
            manufacturer.website = website
            manufacturer.contact_info = contact_info
            manufacturer.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Hersteller erfolgreich aktualisiert',
                'manufacturer': {
                    'id': manufacturer.id,
                    'name': manufacturer.name,
                    'description': manufacturer.description,
                    'website': manufacturer.website,
                    'contact_info': manufacturer.contact_info
                }
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating manufacturer {manufacturer_id}: {e}")
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren des Herstellers'}), 500
    
    # GET request - return manufacturer data for modal
    return jsonify({
        'id': manufacturer.id,
        'name': manufacturer.name,
        'description': manufacturer.description or '',
        'website': manufacturer.website or '',
        'contact_info': manufacturer.contact_info or ''
    })

@manufacturers_bp.route('/delete/<int:manufacturer_id>', methods=['POST'])
@login_required
def delete_manufacturer(manufacturer_id):
    """Delete manufacturer"""
    try:
        manufacturer = Manufacturer.query.get_or_404(manufacturer_id)
        
        # Check if manufacturer has associated assets
        asset_count = db.session.query(Asset).filter(Asset.manufacturers.any(Manufacturer.id == manufacturer_id)).count()
        if asset_count > 0:
            return jsonify({
                'success': False, 
                'message': f'Hersteller kann nicht gelöscht werden. {asset_count} Assets sind diesem Hersteller zugeordnet.'
            }), 400
        
        # Delete manufacturer
        db.session.delete(manufacturer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Hersteller erfolgreich gelöscht'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting manufacturer {manufacturer_id}: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen des Herstellers'}), 500

@manufacturers_bp.route('/api/manufacturers')
@login_required
def api_manufacturers():
    """API endpoint for manufacturer list (for dropdowns, etc.)"""
    try:
        manufacturers = Manufacturer.query.order_by(Manufacturer.name.asc()).all()
        
        return jsonify([{
            'id': manufacturer.id,
            'name': manufacturer.name,
            'description': manufacturer.description,
            'website': manufacturer.website,
            'contact_info': manufacturer.contact_info
        } for manufacturer in manufacturers])
        
    except Exception as e:
        current_app.logger.error(f"Error fetching manufacturers API: {e}")
        return jsonify([]), 500
