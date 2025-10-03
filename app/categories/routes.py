# MD3 Categories Routes - Modern category management interface
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import desc, func

from . import categories_bp
from ..models import db, Category, Asset

@categories_bp.route('/')
@login_required
def categories():
    """MD3 Categories list view"""
    try:
        # Get all categories with asset counts
        categories_data = db.session.query(
            Category.id,
            Category.name,
            Category.description,
            Category.created_at,
            Category.updated_at,
            func.count(Asset.id).label('asset_count')
        ).outerjoin(Asset, Category.id == Asset.category_id)\
        .group_by(Category.id, Category.name, Category.description, Category.created_at, Category.updated_at)\
        .order_by(Category.name.asc()).all()
        
        # Convert to list of dicts for template
        categories_list = []
        for cat_data in categories_data:
            categories_list.append({
                'id': cat_data.id,
                'name': cat_data.name,
                'description': cat_data.description,
                'created_at': cat_data.created_at,
                'updated_at': cat_data.updated_at,
                'asset_count': cat_data.asset_count or 0
            })
        
        return render_template('md3/categories/categories.html', 
                             categories=categories_list,
                             total_categories=len(categories_list))
                             
    except Exception as e:
        current_app.logger.error(f"Error loading categories: {e}")
        flash('Fehler beim Laden der Kategorien', 'error')
        return render_template('md3/categories/categories.html', 
                             categories=[],
                             total_categories=0)

@categories_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_category():
    """Add new category"""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            if not name:
                return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
            
            # Check if category already exists
            existing_category = Category.query.filter_by(name=name).first()
            if existing_category:
                return jsonify({'success': False, 'message': 'Kategorie mit diesem Namen existiert bereits'}), 400
            
            # Create new category
            new_category = Category(
                name=name,
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_category)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Kategorie erfolgreich erstellt',
                'category': {
                    'id': new_category.id,
                    'name': new_category.name,
                    'description': new_category.description,
                    'asset_count': 0
                }
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating category: {e}")
            return jsonify({'success': False, 'message': 'Fehler beim Erstellen der Kategorie'}), 500
    
    # GET request - return to categories list (modal handles form)
    return redirect(url_for('md3_categories.categories'))

@categories_bp.route('/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    """Edit existing category"""
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            
            if not name:
                return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
            
            # Check if another category has this name
            existing_category = Category.query.filter(
                Category.name == name,
                Category.id != category_id
            ).first()
            
            if existing_category:
                return jsonify({'success': False, 'message': 'Kategorie mit diesem Namen existiert bereits'}), 400
            
            # Update category
            category.name = name
            category.description = description
            category.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Kategorie erfolgreich aktualisiert',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description
                }
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating category {category_id}: {e}")
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Kategorie'}), 500
    
    # GET request - return category data for modal
    return jsonify({
        'id': category.id,
        'name': category.name,
        'description': category.description or ''
    })

@categories_bp.route('/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete category"""
    try:
        category = Category.query.get_or_404(category_id)
        
        # Check if category has associated assets
        asset_count = Asset.query.filter_by(category_id=category_id).count()
        if asset_count > 0:
            return jsonify({
                'success': False, 
                'message': f'Kategorie kann nicht gelöscht werden. {asset_count} Assets sind dieser Kategorie zugeordnet.'
            }), 400
        
        # Delete category
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Kategorie erfolgreich gelöscht'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting category {category_id}: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen der Kategorie'}), 500

@categories_bp.route('/api/categories')
@login_required
def api_categories():
    """API endpoint for category list (for dropdowns, etc.)"""
    try:
        categories = Category.query.order_by(Category.name.asc()).all()
        
        return jsonify([{
            'id': category.id,
            'name': category.name,
            'description': category.description
        } for category in categories])
        
    except Exception as e:
        current_app.logger.error(f"Error fetching categories API: {e}")
        return jsonify([]), 500
