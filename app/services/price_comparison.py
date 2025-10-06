"""
Price Comparison Service
Multi-backend architecture for price comparison
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import os
import requests
from flask import current_app
from bs4 import BeautifulSoup
import urllib.parse
import time


class PriceComparisonBackend(ABC):
    """Abstract base class for price comparison backends"""
    
    @abstractmethod
    def search_prices(self, query: str, ean: Optional[str] = None, gtin: Optional[str] = None) -> List[Dict]:
        """
        Search for prices across different shops
        
        Args:
            query: Product name/description
            ean: EAN code (optional)
            gtin: GTIN code (optional)
            
        Returns:
            List of dictionaries with keys: shop, price, url, shipping
        """
        pass


class MockBackend(PriceComparisonBackend):
    """Mock backend for testing and fallback"""
    
    def search_prices(self, query: str, ean: Optional[str] = None, gtin: Optional[str] = None) -> List[Dict]:
        """Return mock data for testing"""
        base_price = 1000.0
        
        return [
            {
                'shop': 'MediaMarkt',
                'price': base_price * 0.92,
                'url': f'https://www.mediamarkt.de/de/search.html?query={query}',
                'shipping': 'Versandkostenfrei'
            },
            {
                'shop': 'Saturn',
                'price': base_price * 0.95,
                'url': f'https://www.saturn.de/de/search.html?query={query}',
                'shipping': 'Versandkostenfrei'
            },
            {
                'shop': 'Amazon',
                'price': base_price * 0.98,
                'url': f'https://www.amazon.de/s?k={query}',
                'shipping': 'Versandkostenfrei ab 29€'
            },
            {
                'shop': 'Cyberport',
                'price': base_price * 1.03,
                'url': f'https://www.cyberport.de/search?query={query}',
                'shipping': 'zzgl. 5,99€ Versand'
            }
        ]


class GoogleShoppingBackend(PriceComparisonBackend):
    """Google Shopping API backend"""
    
    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_CUSTOM_SEARCH_API_KEY')
        self.search_engine_id = os.environ.get('GOOGLE_SHOPPING_ENGINE_ID')
        self.base_url = 'https://www.googleapis.com/customsearch/v1'
        
    def is_configured(self) -> bool:
        """Check if API credentials are configured"""
        return bool(self.api_key and self.search_engine_id)
    
    def search_prices(self, query: str, ean: Optional[str] = None, gtin: Optional[str] = None) -> List[Dict]:
        """Search using Google Shopping API"""
        if not self.is_configured():
            current_app.logger.warning('Google Shopping API not configured, using fallback')
            return []
        
        # Prefer EAN/GTIN for more accurate results
        search_query = ean or gtin or query
        
        try:
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': search_query,
                'num': 5,  # Number of results
            }
            
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Parse Google Shopping results
            for item in data.get('items', []):
                # Extract price from pagemap (if available)
                pagemap = item.get('pagemap', {})
                offer = pagemap.get('offer', [{}])[0]
                product = pagemap.get('product', [{}])[0]
                
                price_str = offer.get('price') or product.get('price', '0')
                try:
                    price = float(price_str.replace(',', '.').replace('€', '').strip())
                except (ValueError, AttributeError):
                    price = 0.0
                
                if price > 0:
                    results.append({
                        'shop': item.get('displayLink', 'Unbekannt'),
                        'price': price,
                        'url': item.get('link', '#'),
                        'shipping': offer.get('availability', 'Keine Info')
                    })
            
            return sorted(results, key=lambda x: x['price'])
            
        except requests.RequestException as e:
            current_app.logger.error(f'Google Shopping API error: {e}')
            return []


class IdealoScraperBackend(PriceComparisonBackend):
    """
    Idealo.de Scraper Backend
    Scrapes prices from Idealo price comparison portal
    """
    
    def __init__(self):
        self.base_url = 'https://www.idealo.de'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search_prices(self, query: str, ean: Optional[str] = None, gtin: Optional[str] = None) -> List[Dict]:
        """Search Idealo for product prices"""
        try:
            # Use EAN if available for better accuracy
            search_query = ean or gtin or query
            encoded_query = urllib.parse.quote(search_query)
            
            search_url = f'{self.base_url}/preisvergleich/MainSearchProductCategory.html?q={encoded_query}'
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Parse Idealo product listings
            # Note: Idealo's HTML structure may change, this is a basic implementation
            product_cards = soup.select('.productOffers-listItem, .product-item')[:5]
            
            for card in product_cards:
                try:
                    # Extract shop name
                    shop_elem = card.select_one('.shop-name, .merchant-name, [data-merchant-name]')
                    shop = shop_elem.text.strip() if shop_elem else 'Unbekannt'
                    
                    # Extract price
                    price_elem = card.select_one('.price, [data-price]')
                    if price_elem:
                        price_text = price_elem.text.strip()
                        # Remove currency symbols and parse
                        price_text = price_text.replace('€', '').replace(',', '.').strip()
                        price = float(price_text.split()[0])
                    else:
                        continue
                    
                    # Extract URL
                    link_elem = card.select_one('a[href]')
                    url = link_elem['href'] if link_elem else '#'
                    if not url.startswith('http'):
                        url = self.base_url + url
                    
                    # Extract shipping info
                    shipping_elem = card.select_one('.shipping-info, .delivery-info')
                    shipping = shipping_elem.text.strip() if shipping_elem else 'zzgl. Versand'
                    
                    results.append({
                        'shop': shop,
                        'price': price,
                        'url': url,
                        'shipping': shipping,
                        'source': 'Idealo'
                    })
                    
                except (ValueError, AttributeError, IndexError) as e:
                    continue
            
            return sorted(results, key=lambda x: x['price'])[:5]
            
        except Exception as e:
            current_app.logger.error(f'Idealo scraper error: {e}')
            return []


class GeizhalsScraperBackend(PriceComparisonBackend):
    """
    Geizhals.de Scraper Backend
    Backup scraper for price comparison
    """
    
    def __init__(self):
        self.base_url = 'https://geizhals.de'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def search_prices(self, query: str, ean: Optional[str] = None, gtin: Optional[str] = None) -> List[Dict]:
        """Search Geizhals for product prices"""
        try:
            search_query = ean or gtin or query
            encoded_query = urllib.parse.quote(search_query)
            
            search_url = f'{self.base_url}/?fs={encoded_query}'
            
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Parse Geizhals product listings
            offers = soup.select('.offer, .merchant')[:5]
            
            for offer in offers:
                try:
                    # Extract shop name
                    shop_elem = offer.select_one('.merchant-name, .shop')
                    shop = shop_elem.text.strip() if shop_elem else 'Unbekannt'
                    
                    # Extract price
                    price_elem = offer.select_one('.price')
                    if price_elem:
                        price_text = price_elem.text.strip()
                        price_text = price_text.replace('€', '').replace(',', '.').replace('−', '-').strip()
                        # Extract first number
                        import re
                        match = re.search(r'(\d+\.?\d*)', price_text)
                        if match:
                            price = float(match.group(1))
                        else:
                            continue
                    else:
                        continue
                    
                    # Extract URL
                    link_elem = offer.select_one('a[href]')
                    url = link_elem['href'] if link_elem else '#'
                    if not url.startswith('http'):
                        url = self.base_url + url
                    
                    # Shipping info
                    shipping = 'zzgl. Versand'
                    
                    results.append({
                        'shop': shop,
                        'price': price,
                        'url': url,
                        'shipping': shipping,
                        'source': 'Geizhals'
                    })
                    
                except (ValueError, AttributeError, IndexError) as e:
                    continue
            
            return sorted(results, key=lambda x: x['price'])[:5]
            
        except Exception as e:
            current_app.logger.error(f'Geizhals scraper error: {e}')
            return []


class InternalSupplierBackend(PriceComparisonBackend):
    """
    Internal B2B Supplier Backend
    Fetches prices from internal AssetSupplierPrice database
    """
    
    def search_prices(self, query: str, ean: Optional[str] = None, gtin: Optional[str] = None, asset_id: Optional[int] = None) -> List[Dict]:
        """Get prices from internal supplier database"""
        try:
            from app.models import AssetSupplierPrice
            
            if not asset_id:
                return []
            
            # Query all prices for this asset
            prices = AssetSupplierPrice.query.filter_by(asset_id=asset_id).filter(
                AssetSupplierPrice.price > 0
            ).all()
            
            results = []
            for price_entry in prices:
                # Check if price is still valid
                if not price_entry.is_valid():
                    continue
                
                results.append({
                    'shop': price_entry.supplier.name,
                    'price': price_entry.price,
                    'url': price_entry.supplier_url or '#',
                    'shipping': price_entry.payment_terms or 'Auf Rechnung',
                    'article_number': price_entry.supplier_article_number,
                    'delivery_time': f'{price_entry.delivery_time_days} Tage' if price_entry.delivery_time_days else 'Auf Anfrage',
                    'last_updated': price_entry.last_updated.strftime('%d.%m.%Y') if price_entry.last_updated else None,
                    'source': 'B2B Lieferant',
                    'is_b2b': True
                })
            
            return sorted(results, key=lambda x: x['price'])
            
        except Exception as e:
            current_app.logger.error(f'Internal supplier backend error: {e}')
            return []


class PriceComparisonService:
    """
    Hybrid Price Comparison Service
    Combines B2B suppliers and WWW price comparison
    """
    
    def __init__(self):
        # B2B backends
        self.b2b_backends = [
            InternalSupplierBackend(),
        ]
        
        # WWW backends (price comparison portals)
        self.www_backends = [
            IdealoScraperBackend(),
            GeizhalsScraperBackend(),
            GoogleShoppingBackend(),  # Optional (API key needed)
            MockBackend(),  # Always available as fallback
        ]
    
    def get_hybrid_prices(self, asset_id: int, asset_name: str, asset_value: float = 0, 
                         ean: Optional[str] = None, gtin: Optional[str] = None) -> Dict:
        """
        Get prices from BOTH B2B suppliers and WWW
        
        Args:
            asset_id: ID of the asset
            asset_name: Name of the asset
            asset_value: Current value/price
            ean: EAN code (optional)
            gtin: GTIN code (optional)
            
        Returns:
            Dictionary with b2b_prices, www_prices, and best overall
        """
        b2b_prices = []
        www_prices = []
        
        # Get B2B supplier prices
        for backend in self.b2b_backends:
            try:
                results = backend.search_prices(asset_name, ean, gtin, asset_id=asset_id)
                if results:
                    b2b_prices.extend(results)
            except Exception as e:
                current_app.logger.error(f'B2B Backend {backend.__class__.__name__} failed: {e}')
        
        # Get WWW prices (price comparison portals)
        for backend in self.www_backends:
            try:
                results = backend.search_prices(asset_name, ean, gtin)
                if results:
                    www_prices.extend(results)
                    break  # Stop after first successful backend
            except Exception as e:
                current_app.logger.error(f'WWW Backend {backend.__class__.__name__} failed: {e}')
                continue
        
        # Sort both lists by price
        b2b_prices = sorted(b2b_prices, key=lambda x: x['price'])
        www_prices = sorted(www_prices, key=lambda x: x['price'])
        
        # Find best prices
        best_b2b = b2b_prices[0] if b2b_prices else None
        best_www = www_prices[0] if www_prices else None
        
        all_prices = b2b_prices + www_prices
        best_overall = sorted(all_prices, key=lambda x: x['price'])[0] if all_prices else None
        
        # Calculate savings
        savings = 0
        if asset_value > 0 and best_overall:
            savings = asset_value - best_overall['price']
        
        return {
            'b2b_prices': b2b_prices[:5],  # Top 5 B2B
            'www_prices': www_prices[:5],  # Top 5 WWW
            'best_b2b_price': best_b2b['price'] if best_b2b else None,
            'best_www_price': best_www['price'] if best_www else None,
            'best_overall_price': best_overall['price'] if best_overall else asset_value,
            'best_overall_source': best_overall.get('source') if best_overall else None,
            'savings': max(0, savings),
            'has_b2b_prices': len(b2b_prices) > 0,
            'has_www_prices': len(www_prices) > 0
        }
    
    def get_best_prices(self, asset_name: str, asset_value: float = 0, 
                       ean: Optional[str] = None, gtin: Optional[str] = None) -> Dict:
        """
        Legacy method for backwards compatibility
        Get best prices from WWW only
        """
        alternatives = []
        
        # Try each WWW backend until we get results
        for backend in self.www_backends:
            try:
                results = backend.search_prices(asset_name, ean, gtin)
                if results:
                    alternatives = results
                    break
            except Exception as e:
                current_app.logger.error(f'Backend {backend.__class__.__name__} failed: {e}')
                continue
        
        # Calculate savings
        best_price = alternatives[0]['price'] if alternatives else asset_value
        savings = asset_value - best_price if asset_value > 0 else 0
        
        return {
            'alternatives': alternatives,
            'best_price': best_price,
            'savings': max(0, savings),
            'backend_used': alternatives[0]['shop'] if alternatives else 'None'
        }
