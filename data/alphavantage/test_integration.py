#!/usr/bin/env python3
"""
Test Alpha Vantage integration - all modules.

Tests:
1. Core API client
2. Equities intraday
3. Options historical
4. Database connectivity
5. Views and functions
"""

import sys
from data.database import query_to_dataframe


def test_api_key():
    """Test API key availability."""
    print("\n" + "="*70)
    print("TEST 1: API Key")
    print("="*70)
    
    try:
        from data.alphavantage.core import get_api_key
        api_key = get_api_key()
        
        if api_key:
            masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
            print(f"✅ API key found: {masked_key}")
            return True
        else:
            print("❌ API key not found")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_database():
    """Test database connection."""
    print("\n" + "="*70)
    print("TEST 2: Database Connection")
    print("="*70)
    
    try:
        # Test basic query
        result = query_to_dataframe("SELECT NOW() as current_time")
        print(f"✅ Database connected: {result['current_time'].iloc[0]}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_intraday_schema():
    """Test intraday data schema."""
    print("\n" + "="*70)
    print("TEST 3: Intraday Data Schema")
    print("="*70)
    
    try:
        # Check table exists
        result = query_to_dataframe("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'market_data_intraday'
        """)
        
        if result.empty:
            print("❌ Table market_data_intraday not found")
            return False
        
        print("✅ Table market_data_intraday exists")
        
        # Check views
        views = ['latest_intraday_prices', 'intraday_data_coverage']
        for view in views:
            result = query_to_dataframe(f"""
                SELECT table_name FROM information_schema.views 
                WHERE table_name = '{view}'
            """)
            if result.empty:
                print(f"❌ View {view} not found")
                return False
            print(f"✅ View {view} exists")
        
        # Check data coverage
        coverage = query_to_dataframe("SELECT * FROM intraday_data_coverage")
        if not coverage.empty:
            print(f"\n📊 Intraday Data Coverage:")
            print(coverage.to_string(index=False))
        else:
            print("\nℹ️  No intraday data yet (run downloader to populate)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_options_schema():
    """Test options data schema."""
    print("\n" + "="*70)
    print("TEST 4: Options Data Schema")
    print("="*70)
    
    try:
        # Check table exists
        result = query_to_dataframe("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'options_data_historical'
        """)
        
        if result.empty:
            print("❌ Table options_data_historical not found")
            return False
        
        print("✅ Table options_data_historical exists")
        
        # Check views
        views = ['latest_options_chain', 'options_data_coverage']
        for view in views:
            result = query_to_dataframe(f"""
                SELECT table_name FROM information_schema.views 
                WHERE table_name = '{view}'
            """)
            if result.empty:
                print(f"❌ View {view} not found")
                return False
            print(f"✅ View {view} exists")
        
        # Check functions
        functions = ['get_option_chain', 'get_options_summary']
        for func in functions:
            result = query_to_dataframe(f"""
                SELECT proname FROM pg_proc 
                WHERE proname = '{func}'
            """)
            if result.empty:
                print(f"❌ Function {func} not found")
                return False
            print(f"✅ Function {func} exists")
        
        # Check data coverage
        coverage = query_to_dataframe("SELECT * FROM options_data_coverage")
        if not coverage.empty:
            print(f"\n📊 Options Data Coverage:")
            print(coverage.to_string(index=False))
        else:
            print("\nℹ️  No options data yet (run downloader to populate)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """Test module imports."""
    print("\n" + "="*70)
    print("TEST 5: Module Imports")
    print("="*70)
    
    try:
        # Core
        from data.alphavantage.core import make_api_request, get_api_key, enforce_rate_limit
        print("✅ Core module imports successful")
        
        # Equities
        from data.alphavantage.equities import (
            fetch_intraday_data,
            download_symbol_intraday,
            download_multiple_symbols
        )
        print("✅ Equities module imports successful")
        
        # Options
        from data.alphavantage.options import (
            fetch_historical_options,
            download_options_for_symbol,
            download_options_for_multiple_symbols
        )
        print("✅ Options module imports successful")
        
        # Main module
        from data.alphavantage import (
            make_api_request,
            fetch_intraday_data,
            fetch_historical_options
        )
        print("✅ Main module imports successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("🧪 ALPHA VANTAGE INTEGRATION TESTS")
    print("="*70)
    
    tests = [
        ("API Key", test_api_key),
        ("Database", test_database),
        ("Intraday Schema", test_intraday_schema),
        ("Options Schema", test_options_schema),
        ("Module Imports", test_imports),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS SUMMARY")
    print("="*70)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        print("\nNext steps:")
        print("  1. Download intraday data:")
        print("     python -m data.alphavantage.equities.intraday")
        print("  2. Download options data:")
        print("     python -m data.alphavantage.options.historical")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

