from app import create_app
from app.models import db, Asset
import sys

app = create_app()
with app.app_context():
    print('Aktuelle Status-Verteilung:')
    for status in db.session.query(Asset.status).distinct().all():
        count = Asset.query.filter_by(status=status[0]).count()
        print(f'- {status[0]}: {count} Assets')
    
    # Überprüfen der letzten importierten Assets
    print('\nLetzte 5 Assets:')
    last_assets = Asset.query.order_by(Asset.id.desc()).limit(5).all()
    for asset in last_assets:
        print(f'ID: {asset.id}, Name: {asset.name}, Status: {asset.status}, Standort: {asset.location_id}')
    
    # Prüfen, ob Parameter zum Ändern der Status übergeben wurde
    if len(sys.argv) > 1 and sys.argv[1] == 'activate':
        print('\nAktiviere inaktive Assets...')
        inactive_assets = Asset.query.filter_by(status='inactive').all()
        activated_count = 0
        
        for asset in inactive_assets:
            asset.status = 'active'
            activated_count += 1
        
        db.session.commit()
        print(f'{activated_count} Assets wurden auf "active" gesetzt.')
        
        # Status-Verteilung nach dem Update anzeigen
        print('\nNeue Status-Verteilung:')
        for status in db.session.query(Asset.status).distinct().all():
            count = Asset.query.filter_by(status=status[0]).count()
            print(f'- {status[0]}: {count} Assets')
