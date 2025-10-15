"""
Shared API client for all Alpha Vantage requests.

Handles authentication, rate limiting, and error handling.
"""

import os
import time
import requests
from typing import Optional, Dict, Any
from datetime import datetime


# API Configuration
BASE_URL = 'https://www.alphavantage.co/query'
RATE_LIMIT_DELAY = 15  # seconds between requests (5 calls/min = 12s, we use 15 for safety)

# Rate limiting state
_last_api_call = None


def get_api_key() -> str:
    """
    Get API key from environment or prompt user.
    
    Returns:
        API key string
    
    Raises:
        ValueError: If API key not found and user doesn't provide one
    """
    api_key = os.getenv('ALPHAVANTAGE_API_KEY')
    
    if not api_key:
        print("❌ ALPHAVANTAGE_API_KEY not found in environment")
        api_key = input("Enter your Alpha Vantage API key: ").strip()
        
        if not api_key:
            raise ValueError("API key is required")
    
    return api_key


def enforce_rate_limit():
    """
    Ensure minimum time between API calls.
    
    Free tier: 25 calls/day, 5 calls/minute
    We enforce 15 seconds between calls to stay under limit.
    """
    global _last_api_call
    
    if _last_api_call is not None:
        elapsed = (datetime.now() - _last_api_call).total_seconds()
        if elapsed < RATE_LIMIT_DELAY:
            wait_time = RATE_LIMIT_DELAY - elapsed
            print(f"  ⏱️  Rate limit: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    _last_api_call = datetime.now()


def make_api_request(
    params: Dict[str, Any],
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Make a request to Alpha Vantage API.
    
    Args:
        params: API parameters (without apikey - added automatically)
        timeout: Request timeout in seconds
    
    Returns:
        JSON response from API
    
    Raises:
        ValueError: On API errors or invalid responses
        requests.RequestException: On network errors
    
    Example:
        >>> params = {'function': 'TIME_SERIES_DAILY', 'symbol': 'IBM'}
        >>> data = make_api_request(params)
    """
    # Add API key
    params['apikey'] = get_api_key()
    
    # Enforce rate limiting
    enforce_rate_limit()
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        
        # Check for API errors
        if 'Error Message' in data:
            raise ValueError(f"API Error: {data['Error Message']}")
        
        if 'Note' in data:
            raise ValueError(f"Rate Limited: {data['Note']}")
        
        if 'Information' in data:
            raise ValueError(f"API Limit: {data['Information']}")
        
        return data
        
    except requests.exceptions.Timeout:
        raise ValueError(f"Request timeout ({timeout}s)")
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Request error: {str(e)}")

