from flask import request, jsonify, current_app as app
from .models import Asset
from . import db

def init_api_routes(app):
    """API-Routen für AJAX-Requests"""
    
    @app.route('/api/assets/details', methods=['POST'])
    def get_assets_details():
        """API-Endpoint um Asset-Details für das Gruppendetails-Modal zu laden"""
        try:
            data = request.get_json()
            if not data or 'asset_ids' not in data:
                return jsonify({'success': False, 'message': 'Asset-IDs sind erforderlich'}), 400
            
            asset_ids = data['asset_ids']
            if not isinstance(asset_ids, list):
                return jsonify({'success': False, 'message': 'Asset-IDs müssen eine Liste sein'}), 400
            
            # Asset-IDs zu Integers konvertieren
            try:
                asset_ids = [int(id) for id in asset_ids]
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': 'Ungültige Asset-IDs'}), 400
            
            # Assets aus der Datenbank laden
            assets = Asset.query.filter(Asset.id.in_(asset_ids)).all()
            
            # Asset-Daten für das Frontend aufbereiten
            assets_data = []
            for asset in assets:
                asset_data = {
                    'id': asset.id,
                    'name': asset.name,
                    'article_number': asset.article_number,
                    'value': float(asset.value) if asset.value else None,
                    'status': asset.status,
                    'category': {
                        'id': asset.category.id,
                        'name': asset.category.name
                    } if asset.category else None,
                    'manufacturer': {
                        'id': asset.manufacturers[0].id,
                        'name': asset.manufacturers[0].name
                    } if asset.manufacturers else None,
                    'supplier': {
                        'id': asset.suppliers[0].id,
                        'name': asset.suppliers[0].name
                    } if asset.suppliers else None,
                    'location': asset.location,
                    'assignments': [{
                        'id': assignment.id,
                        'name': assignment.name
                    } for assignment in asset.assignments] if asset.assignments else []
                }
                assets_data.append(asset_data)
            
            return jsonify({
                'success': True,
                'assets': assets_data,
                'count': len(assets_data)
            })
            
        except Exception as e:
            app.logger.error(f'Fehler beim Laden der Asset-Details: {e}')
            return jsonify({
                'success': False,
                'message': f'Fehler beim Laden der Asset-Details: {str(e)}'
            }), 500
