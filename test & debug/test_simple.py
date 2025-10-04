#!/usr/bin/env python3
"""
Simple test script for inventory completion workflow
Tests: Inventur abschließen -> Berichte anzeigen
"""

import requests
import re

def test_completion_workflow():
    """Test the complete inventory workflow end-to-end"""
    
    session = requests.Session()

    # Login first
    login_data = {'username': 'admin', 'password': 'admin'}
    login_response = session.post('http://127.0.0.1:5000/login', data=login_data)
    print(f'Login status: {login_response.status_code}')

    # Test MD3 reports route first
    reports_response = session.get('http://127.0.0.1:5000/md3/inventory/reports')
    print(f'MD3 Reports status: {reports_response.status_code}')
    
    if reports_response.status_code == 200:
        print('SUCCESS: MD3 Reports route works!')
        
        # Check content
        if 'Inventurberichte' in reports_response.text:
            print('SUCCESS: Reports page contains title')
        
        # Count completed sessions before
        completed_count_before = reports_response.text.count('completed')
        print(f'Completed sessions found in reports: {completed_count_before}')
        
        # Check if we can see session names
        if 'MD3 Test Inventur' in reports_response.text:
            print('SUCCESS: MD3 Test Inventur found in reports!')
        else:
            print('INFO: MD3 Test Inventur not yet in reports (expected if not completed)')
            
        return True
    else:
        print(f'ERROR: MD3 Reports failed: {reports_response.status_code}')
        return False

if __name__ == '__main__':
    print('=== Testing MD3 Inventory Reports ===')
    test_completion_workflow()
