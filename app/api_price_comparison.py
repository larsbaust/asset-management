"""
Price Comparison API
Provides price comparison functionality for assets
"""

from flask import Blueprint, jsonify, current_app
from flask_login import login_required
from app.models import Asset
from app.services import PriceComparisonService

api_price_bp = Blueprint('api_price', __name__, url_prefix='/api')

@api_price_bp.route('/price-comparison/<int:asset_id>', methods=['GET'])
@login_required
def price_comparison(asset_id):
    """
    Get hybrid price comparison for an asset
    Returns B2B supplier prices AND WWW prices separately
    """
    asset = Asset.query.get_or_404(asset_id)
    
    # Initialize price comparison service
    service = PriceComparisonService()
    
    # Get hybrid prices (B2B + WWW)
    try:
        result = service.get_hybrid_prices(
            asset_id=asset.id,
            asset_name=asset.name,
            asset_value=asset.value or 0,
            ean=asset.ean,
            gtin=asset.gtin
        )
        
        b2b_prices = result['b2b_prices']
        www_prices = result['www_prices']
        best_overall_price = result['best_overall_price']
        savings = result['savings']
        
    except Exception as e:
        current_app.logger.error(f'Price comparison error for asset {asset_id}: {e}')
        # Fallback to empty results
        b2b_prices = []
        www_prices = []
        best_overall_price = asset.value or 0
        savings = 0
    
    our_price = asset.value if asset.value else 0
    
    return jsonify({
        'success': True,
        'asset_id': asset.id,
        'asset_name': asset.name,
        'ean': asset.ean,
        'gtin': asset.gtin,
        'our_price': our_price,
        'best_price': best_overall_price,
        'savings': savings,
        # Hybrid results
        'b2b_prices': b2b_prices,
        'www_prices': www_prices,
        'has_b2b': len(b2b_prices) > 0,
        'has_www': len(www_prices) > 0
    })
