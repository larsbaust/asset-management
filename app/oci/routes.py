"""
OCI Routes - HTTP Endpoints for OCI Integration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_required, current_user
from app.oci.service import OCIService
from app.oci.config import OCIConfig

oci_bp = Blueprint('oci', __name__, url_prefix='/oci')


@oci_bp.route('/outbound', methods=['GET', 'POST'])
@login_required
def outbound():
    """
    OCI Outbound - Open shop.api.de catalog
    Redirects user to external catalog with OCI parameters
    """
    
    # Build OCI request
    oci_service = OCIService()
    request_data = oci_service.build_outbound_request(
        user_id=current_user.username if current_user else None
    )
    
    # Store context in session for inbound callback
    session['oci_context'] = {
        'user_id': current_user.id,
        'username': current_user.username,
        'started_at': str(request.headers.get('User-Agent', ''))
    }
    session.permanent = True  # Session bleibt länger bestehen
    
    # Debug mode: Show fields before sending (add ?debug=1 to URL)
    if request.args.get('debug') == '1':
        return render_template('oci/debug_outbound.html', 
                              oci_url=OCIConfig.get_outbound_url(),
                              oci_data=request_data)
    
    # Render intermediate page that auto-submits form to shop.api.de
    return render_template('oci/outbound.html', 
                          oci_url=OCIConfig.get_outbound_url(),
                          oci_data=request_data)


@oci_bp.route('/inbound', methods=['POST'])
def inbound():
    """
    OCI Inbound - Receive shopping cart from shop.api.de
    This is called by shop.api.de after user completes selection
    
    Public endpoint (no @login_required, no @csrf_exempt) as it's called by external system
    """
    
    # DEBUG: Log alle empfangenen Daten
    print("\n" + "="*80)
    print("🔍 OCI INBOUND DEBUG - Empfangene Daten:")
    print("="*80)
    for key, value in request.form.items():
        print(f"  {key}: {value}")
    print("="*80 + "\n")
    
    # Parse OCI response
    oci_service = OCIService()
    items = oci_service.parse_inbound_response(request.form)
    
    print(f"✅ Geparste Items: {len(items) if items else 0}")
    if items:
        for idx, item in enumerate(items, 1):
            print(f"  Item {idx}: {item.get('description', 'N/A')} - {item.get('price', 0)}€")
    print("\n")
    
    if not items:
        flash('Keine Artikel im Warenkorb gefunden. Bitte Logs prüfen.', 'warning')
        return redirect(url_for('order.wizard_step1', md3=1))
    
    # Get context from session
    oci_context = session.get('oci_context', {})
    user_id = oci_context.get('user_id')
    
    if not user_id:
        # Fallback: Try to get user from login
        flash('Sitzung abgelaufen. Bitte erneut anmelden.', 'warning')
        # Store items temporarily
        session['oci_cart'] = {
            'items': items,
            'supplier': 'shop.api.de',
            'received_at': str(request.form)
        }
        return redirect(url_for('auth.login', next=url_for('oci.confirm_and_redirect')))
    
    try:
        # ✅ Auto-create assets direkt beim Inbound
        assets = oci_service.create_or_update_assets_from_oci(items, user_id)
        
        # Get shop.api.de supplier
        from app.models import Supplier
        supplier = Supplier.query.filter_by(name='shop.api.de').first()
        
        # ✅ Initialize Wizard Session with shop.api.de supplier
        WIZARD_SESSION_KEY = 'order_wizard_data'
        if WIZARD_SESSION_KEY not in session:
            session[WIZARD_SESSION_KEY] = {}
        
        # Set supplier_id so Step 2 doesn't redirect back to Step 1
        session[WIZARD_SESSION_KEY]['supplier_id'] = supplier.id if supplier else -1
        session[WIZARD_SESSION_KEY]['location_id'] = 0  # Optional location
        session[WIZARD_SESSION_KEY]['budget'] = None
        
        # Store asset IDs in session for wizard
        session['oci_asset_ids'] = [asset.id for asset in assets]
        session['oci_supplier'] = 'shop.api.de'
        
        flash(f'✅ {len(assets)} Artikel aus shop.api.de importiert!', 'success')
        
        # ✅ Redirect direkt zu Step 2 (nicht zu cart-preview)
        return redirect(url_for('md3_order.wizard_step2'))
        
    except Exception as e:
        print(f"❌ Fehler beim Asset-Import: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Fehler beim Importieren: {str(e)}', 'error')
        return redirect(url_for('md3_order.wizard_step1'))


@oci_bp.route('/cart-preview', methods=['GET'])
def cart_preview():
    """
    Preview OCI cart before creating order
    Note: No @login_required - we handle authentication via oci_context
    """
    # DEBUG
    print("\n🔍 CART PREVIEW DEBUG:")
    print(f"  Session Keys: {list(session.keys())}")
    print(f"  current_user.is_authenticated: {current_user.is_authenticated if current_user else False}")
    print(f"  OCI Cart in Session: {'oci_cart' in session}")
    
    # Check if user is authenticated
    if not current_user.is_authenticated:
        # Try to restore user from oci_context
        oci_context = session.get('oci_context', {})
        user_id = oci_context.get('user_id')
        
        if user_id:
            from app.models import User
            from flask_login import login_user
            user = User.query.get(user_id)
            if user:
                login_user(user)
                print(f"  ✅ User {user.username} automatisch eingeloggt (via OCI-Context)")
            else:
                flash('Sitzung abgelaufen. Bitte erneut anmelden.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
        else:
            flash('Sitzung abgelaufen. Bitte erneut anmelden.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
    
    oci_cart = session.get('oci_cart', {})
    items = oci_cart.get('items', [])
    
    print(f"  Items Count: {len(items)}")
    print("\n")
    
    if not items:
        flash('Kein OCI-Warenkorb vorhanden.', 'info')
        return redirect(url_for('md3_order.wizard_step1'))
    
    # Calculate totals
    total_value = sum(item['price'] * item['quantity'] for item in items)
    total_items = sum(item['quantity'] for item in items)
    
    return render_template('oci/cart_preview.html',
                          items=items,
                          total_value=total_value,
                          total_items=total_items,
                          md3=request.args.get('md3', 1))


@oci_bp.route('/confirm-cart', methods=['POST'])
@login_required
def confirm_cart():
    """
    Confirm OCI cart and create order
    """
    oci_cart = session.get('oci_cart', {})
    items = oci_cart.get('items', [])
    
    if not items:
        return jsonify({'success': False, 'message': 'Kein Warenkorb vorhanden'})
    
    try:
        # Create or update assets
        oci_service = OCIService()
        assets = oci_service.create_or_update_assets_from_oci(items, current_user.id)
        
        # Store asset IDs in session for order wizard
        session['oci_asset_ids'] = [asset.id for asset in assets]
        
        # Clear OCI cart
        session.pop('oci_cart', None)
        
        flash(f'{len(assets)} Assets aus OCI-Warenkorb erstellt/aktualisiert!', 'success')
        return jsonify({
            'success': True, 
            'redirect': url_for('md3_order.wizard_step2')
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Fehler beim Erstellen der Assets: {str(e)}'
        })


@oci_bp.route('/confirm-and-redirect', methods=['GET'])
@login_required
def confirm_and_redirect():
    """
    Fallback after login: Process OCI cart if exists
    """
    oci_cart = session.get('oci_cart', {})
    items = oci_cart.get('items', [])
    
    if not items:
        flash('Kein OCI-Warenkorb vorhanden.', 'info')
        return redirect(url_for('md3_order.wizard_step1'))
    
    try:
        oci_service = OCIService()
        assets = oci_service.create_or_update_assets_from_oci(items, current_user.id)
        
        # Get shop.api.de supplier
        from app.models import Supplier
        supplier = Supplier.query.filter_by(name='shop.api.de').first()
        
        # ✅ Initialize Wizard Session with shop.api.de supplier
        WIZARD_SESSION_KEY = 'order_wizard_data'
        if WIZARD_SESSION_KEY not in session:
            session[WIZARD_SESSION_KEY] = {}
        
        session[WIZARD_SESSION_KEY]['supplier_id'] = supplier.id if supplier else -1
        session[WIZARD_SESSION_KEY]['location_id'] = 0
        session[WIZARD_SESSION_KEY]['budget'] = None
        
        session['oci_asset_ids'] = [asset.id for asset in assets]
        session['oci_supplier'] = oci_cart.get('supplier', 'shop.api.de')
        session.pop('oci_cart', None)
        
        flash(f'✅ {len(assets)} Artikel aus shop.api.de importiert!', 'success')
        return redirect(url_for('md3_order.wizard_step2'))
        
    except Exception as e:
        flash(f'Fehler beim Importieren: {str(e)}', 'error')
        return redirect(url_for('md3_order.wizard_step1'))


@oci_bp.route('/cancel', methods=['GET'])
@login_required
def cancel():
    """
    Cancel OCI operation
    """
    session.pop('oci_cart', None)
    session.pop('oci_context', None)
    session.pop('oci_asset_ids', None)
    session.pop('oci_supplier', None)
    flash('OCI-Bestellung abgebrochen.', 'info')
    return redirect(url_for('md3_order.wizard_step1'))


@oci_bp.route('/test-inbound', methods=['GET', 'POST'])
@login_required
def test_inbound():
    """
    Test OCI inbound with sample data (for development)
    """
    if request.method == 'POST':
        # Simulate OCI response
        test_data = {
            'NEW_ITEM-QUANTITY[1]': '2',
            'NEW_ITEM-VENDORMAT[1]': 'TEST-SKU-001',
            'NEW_ITEM-DESCRIPTION[1]': 'Test Laptop Dell XPS 13',
            'NEW_ITEM-PRICE[1]': '1199.00',
            'NEW_ITEM-CURRENCY[1]': 'EUR',
            'NEW_ITEM-UNIT[1]': 'ST',
            'NEW_ITEM-VENDOR[1]': 'shop.api.de',
            'NEW_ITEM-LEADTIME[1]': '3',
            'NEW_ITEM-PRICEUNIT[1]': '1',
            'NEW_ITEM-CUST_FIELD1[1]': '19%',
        }
        
        # Forward to inbound handler
        with oci_bp.test_request_context('/oci/inbound', method='POST', data=test_data):
            return inbound()
    
    return render_template('oci/test_inbound.html')
