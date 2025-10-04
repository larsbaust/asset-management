#!/usr/bin/env python3
"""
Test script for inventory completion workflow
Tests: Inventur abschließen -> Berichte anzeigen
"""

import requests
import re
from app import create_app
from app.models import InventorySession, db

def test_completion_workflow():
    """Test the complete inventory workflow end-to-end"""
    
    # Test the complete inventory workflow
    session = requests.Session()

    # Login first
    login_data = {'username': 'admin', 'password': 'admin'}
    login_response = session.post('http://127.0.0.1:5000/login', data=login_data)
    print(f'Login status: {login_response.status_code}')

    # Get CSRF token from login page
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', login_response.text)
    csrf_token = csrf_match.group(1) if csrf_match else None
    print(f'CSRF token found: {csrf_token is not None}')

    # Test completing an active inventory session (ID 28: MD3 Test Inventur)
    if csrf_token:
        complete_data = {'csrf_token': csrf_token}
        complete_response = session.post('http://127.0.0.1:5000/md3/inventory/planning/28/complete', 
                                       data=complete_data)
        print(f'Complete inventory status: {complete_response.status_code}')
        print(f'Complete response: {complete_response.text[:300]}')
        
        # Now check if the completed session appears in reports
        reports_response = session.get('http://127.0.0.1:5000/md3/inventory/reports')
        print(f'Reports after completion status: {reports_response.status_code}')
        
        # Check if 'MD3 Test Inventur' appears in the reports
        if 'MD3 Test Inventur' in reports_response.text:
            print('✅ SUCCESS: Completed inventory appears in reports!')
        else:
            print('❌ ISSUE: Completed inventory not found in reports')
            
        return True
    else:
        print('❌ Could not get CSRF token')
        return False

def check_database_status():
    """Check the database status of inventory sessions"""
    app = create_app()
    with app.app_context():
        # Check session 28 status
        session_28 = InventorySession.query.get(28)
        if session_28:
            print(f'Session 28 status: {session_28.status}')
            print(f'Session 28 name: {session_28.name}')
            print(f'Session 28 end_date: {session_28.end_date}')
        else:
            print('Session 28 not found')
            
        # Check all completed sessions
        completed = InventorySession.query.filter_by(status='completed').count()
        print(f'Total completed sessions: {completed}')

if __name__ == '__main__':
    print('=== Testing Inventory Completion Workflow ===')
    check_database_status()
    print('\n=== Testing API Workflow ===')
    test_completion_workflow()
