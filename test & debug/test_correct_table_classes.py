#!/usr/bin/env python3
"""
Test Correct Table Classes - Korrigierte Suche nach echten CSS-Klassen
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def test_correct_table_classes():
    app = create_app()
    
    with app.app_context():
        print("=== CORRECT TABLE CLASSES TEST ===")
        
        with app.test_client() as client:
            # Test MD3 Assets Route
            response = client.get('/md3/assets')
            print(f"[HTTP] Status: {response.status_code}")
            
            if response.status_code == 200:
                html_content = response.get_data(as_text=True)
                
                # Korrekte CSS-Klassen suchen
                md3_grouped_asset = html_content.count('md3-grouped-asset')
                table_rows_tr = html_content.count('<tr class=')
                table_rows_total = html_content.count('<tr ')
                
                print(f"[TABLE] <tr class= Zeilen: {table_rows_tr}")
                print(f"[TABLE] Total <tr Zeilen: {table_rows_total}")
                print(f"[TABLE] md3-grouped-asset: {md3_grouped_asset}")
                
                # Asset Tabelle Container suchen
                if 'md3-asset-table-container' in html_content:
                    print("[TABLE] md3-asset-table-container gefunden")
                else:
                    print("[TABLE] md3-asset-table-container FEHLT")
                
                # JavaScript Funktionen suchen
                js_functions = [
                    'openNewAssetModal',
                    'filterAssets',
                    'showAssetDetails',
                    'editAsset',
                    'deleteAsset'
                ]
                
                print(f"\n=== JAVASCRIPT FUNCTIONS ===")
                for func in js_functions:
                    if func in html_content:
                        print(f"[JS] {func}: FOUND")
                    else:
                        print(f"[JS] {func}: MISSING")
                
                # Filter Container suchen
                if 'filter-container' in html_content or 'md3-filter' in html_content:
                    print(f"\n[FILTER] Filter Container gefunden")
                else:
                    print(f"\n[FILTER] Filter Container FEHLT")
                
                # Script Tags zählen
                script_tags = html_content.count('<script>')
                print(f"[JS] Script Tags: {script_tags}")
                
                # Assets für Bielefeld mit Filtern testen
                print(f"\n=== BIELEFELD FILTER TEST ===")
                response_bielefeld = client.get('/md3/assets?location=Frittenwerk Bielefeld')
                
                if response_bielefeld.status_code == 200:
                    bielefeld_html = response_bielefeld.get_data(as_text=True)
                    bielefeld_rows = bielefeld_html.count('<tr ')
                    
                    print(f"[FILTER] Bielefeld Response Status: {response_bielefeld.status_code}")
                    print(f"[FILTER] Bielefeld <tr Zeilen: {bielefeld_rows}")
                    
                    # Prüfe ob spezifische Assets sichtbar sind
                    synology_count = bielefeld_html.count('Synology NAS DS723+')
                    brother_count = bielefeld_html.count('Brother')
                    
                    print(f"[FILTER] Synology Assets: {synology_count}")
                    print(f"[FILTER] Brother Assets: {brother_count}")
                else:
                    print(f"[FILTER] Bielefeld Filter Fehler: {response_bielefeld.status_code}")

if __name__ == "__main__":
    test_correct_table_classes()
