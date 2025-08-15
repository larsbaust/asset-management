#!/usr/bin/env python3
"""
Test script to complete inventory session 28 and verify it appears in reports
"""

import requests
import re
from bs4 import BeautifulSoup

def test_complete_inventory():
    """Test completing inventory session 28 and checking reports"""
    
    session = requests.Session()

    # Login first
    login_data = {'username': 'admin', 'password': 'admin'}
    login_response = session.post('http://127.0.0.1:5000/login', data=login_data)
    print(f'Login status: {login_response.status_code}')

    if login_response.status_code != 200:
        print('Login failed!')
        return False

    # Get the execution page to find CSRF token
    execution_response = session.get('http://127.0.0.1:5000/md3/inventory/planning/28')
    print(f'Execution page status: {execution_response.status_code}')
    
    # Extract CSRF token
    soup = BeautifulSoup(execution_response.text, 'html.parser')
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    csrf_token = csrf_input['value'] if csrf_input else None
    print(f'CSRF token found: {csrf_token is not None}')

    if not csrf_token:
        print('No CSRF token found!')
        return False

    # Complete the inventory session
    complete_data = {'csrf_token': csrf_token}
    complete_response = session.post('http://127.0.0.1:5000/md3/inventory/planning/28/complete', 
                                   data=complete_data,
                                   headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    print(f'Complete inventory status: {complete_response.status_code}')
    print(f'Complete response content: {complete_response.text[:500]}')
    
    # Check if it's JSON response
    try:
        import json
        response_json = complete_response.json()
        print(f'JSON response: {response_json}')
        
        if response_json.get('success'):
            print('SUCCESS: Inventory completed successfully!')
            
            # Now check reports
            reports_response = session.get('http://127.0.0.1:5000/md3/inventory/reports')
            print(f'Reports after completion status: {reports_response.status_code}')
            
            if 'MD3 Test Inventur' in reports_response.text:
                print('SUCCESS: Completed inventory appears in reports!')
                return True
            else:
                print('ISSUE: Completed inventory not found in reports')
                return False
        else:
            print(f'ERROR: Inventory completion failed: {response_json.get("message")}')
            return False
            
    except Exception as e:
        print(f'Error parsing response: {e}')
        return False

if __name__ == '__main__':
    print('=== Testing Inventory Completion Workflow ===')
    test_complete_inventory()
