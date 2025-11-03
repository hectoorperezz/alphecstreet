"""
Download historical options data from Alpha Vantage.

Includes: Pricing (last, mark, bid/ask), Greeks (delta, gamma, theta, vega, rho), and IV
Coverage: 15+ years of historical data (from 2008-01-01)
"""

import sys
import argparse
from typing import Optional, List, Tuple
import pandas as pd
from datetime import datetime

from data.alphavantage.core.api_client import make_api_request
from data.database import get_db_connection, query_to_dataframe, DatabaseConfig


def fetch_historical_options(
    symbol: str,
    date: Optional[str] = None
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Fetch historical options data from Alpha Vantage.
    
    Includes: OHLCV + Greeks (delta, gamma, theta, vega, rho) + IV
    
    Args:
        symbol: Underlying stock symbol (e.g., 'AAPL', 'SPY')
        date: Specific date (YYYY-MM-DD) or None for previous trading session
    
    Returns:
        Tuple of (DataFrame, error_message)
        
    DataFrame columns:
        - contractID, symbol, expiration, strike, type
        - last, mark, bid, bid_size, ask, ask_size
        - volume, open_interest
        - delta, gamma, theta, vega, rho
        - implied_volatility
        - date
    
    Example:
        # Get most recent options chain
        df, err = fetch_historical_options('AAPL')
        
        # Get specific date
        df, err = fetch_historical_options('AAPL', '2025-10-15')
    """
    params = {
        'function': 'HISTORICAL_OPTIONS',
        'symbol': symbol,
    }
    
    if date:
        params['date'] = date
    
    print(f"  📥 Fetching historical options for {symbol}" + 
          (f" (date: {date})" if date else " (latest)") + "...")
    
    try:
        data = make_api_request(params)
        
        if 'data' not in data:
            return None, f"No option data returned for {symbol}"
        
        # Convert to DataFrame
        df = pd.DataFrame(data['data'])
        
        if df.empty:
            return None, f"Empty option data for {symbol}"
        
        print(f"  ✅ Fetched {len(df)} option contracts")
        
        # Show summary
        if 'type' in df.columns:
            calls = len(df[df['type'] == 'call'])
            puts = len(df[df['type'] == 'put'])
            print(f"     Calls: {calls}, Puts: {puts}")
        
        if 'delta' in df.columns:
            print(f"     Greeks: ✅ (delta, gamma, theta, vega, rho)")
        
        if 'implied_volatility' in df.columns:
            print(f"     IV: ✅")
        
        return df, None
        
    except Exception as e:
        return None, str(e)


def insert_options_data(
    df: pd.DataFrame,
    config: Optional[DatabaseConfig] = None
) -> Tuple[int, int]:
    """
    Insert historical options data into database.
    
    FIXED: Uses individual transactions to avoid "transaction aborted" error.
    """
    if config is None:
        config = DatabaseConfig.from_env()
    
    inserted = 0
    updated = 0
    skipped = 0
    errors = []
    
    with get_db_connection(config) as conn:
        for idx, row in df.iterrows():
            try:
                # START NEW TRANSACTION FOR EACH ROW
                with conn.cursor() as cursor:
                    # Check if contract already exists
                    cursor.execute(
                        "SELECT 1 FROM options_data_historical WHERE contractid = %s AND date = %s",
                        (row['contractID'], row.get('date'))
                    )
                    
                    if cursor.fetchone():
                        # Update existing
                        cursor.execute("""
                            UPDATE options_data_historical
                            SET 
                                symbol = %s,
                                expiration = %s,
                                strike = %s,
                                type = %s,
                                last = %s,
                                mark = %s,
                                bid = %s,
                                bid_size = %s,
                                ask = %s,
                                ask_size = %s,
                                volume = %s,
                                open_interest = %s,
                                date = %s,
                                implied_volatility = %s,
                                delta = %s,
                                gamma = %s,
                                theta = %s,
                                vega = %s,
                                rho = %s
                            WHERE contractid = %s AND date = %s
                        """, (
                            row['symbol'],
                            row['expiration'],
                            float(row['strike']),
                            row['type'],
                            float(row.get('last', 0)) if row.get('last') else None,
                            float(row.get('mark', 0)) if row.get('mark') else None,
                            float(row.get('bid', 0)) if row.get('bid') else None,
                            int(row.get('bid_size', 0)) if row.get('bid_size') else None,
                            float(row.get('ask', 0)) if row.get('ask') else None,
                            int(row.get('ask_size', 0)) if row.get('ask_size') else None,
                            int(row.get('volume', 0)) if row.get('volume') else None,
                            int(row.get('open_interest', 0)) if row.get('open_interest') else None,
                            row.get('date'),
                            float(row.get('implied_volatility', 0)) if row.get('implied_volatility') else None,
                            float(row.get('delta', 0)) if row.get('delta') else None,
                            float(row.get('gamma', 0)) if row.get('gamma') else None,
                            float(row.get('theta', 0)) if row.get('theta') else None,
                            float(row.get('vega', 0)) if row.get('vega') else None,
                            float(row.get('rho', 0)) if row.get('rho') else None,
                            row['contractID'],
                            row.get('date')
                        ))
                        updated += 1
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO options_data_historical (
                                contractid, symbol, expiration, strike, type,
                                last, mark, bid, bid_size, ask, ask_size,
                                volume, open_interest, date,
                                implied_volatility, delta, gamma, theta, vega, rho
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """, (
                            row['contractID'],
                            row['symbol'],
                            row['expiration'],
                            float(row['strike']),
                            row['type'],
                            float(row.get('last', 0)) if row.get('last') else None,
                            float(row.get('mark', 0)) if row.get('mark') else None,
                            float(row.get('bid', 0)) if row.get('bid') else None,
                            int(row.get('bid_size', 0)) if row.get('bid_size') else None,
                            float(row.get('ask', 0)) if row.get('ask') else None,
                            int(row.get('ask_size', 0)) if row.get('ask_size') else None,
                            int(row.get('volume', 0)) if row.get('volume') else None,
                            int(row.get('open_interest', 0)) if row.get('open_interest') else None,
                            row.get('date'),
                            float(row.get('implied_volatility', 0)) if row.get('implied_volatility') else None,
                            float(row.get('delta', 0)) if row.get('delta') else None,
                            float(row.get('gamma', 0)) if row.get('gamma') else None,
                            float(row.get('theta', 0)) if row.get('theta') else None,
                            float(row.get('vega', 0)) if row.get('vega') else None,
                            float(row.get('rho', 0)) if row.get('rho') else None
                        ))
                        inserted += 1
                
                # COMMIT THIS ROW
                conn.commit()
                
            except Exception as e:
                # ROLLBACK THIS ROW ONLY
                conn.rollback()
                error_msg = f"Contract {row.get('contractID', 'UNKNOWN')}: {str(e)}"
                errors.append(error_msg)
                skipped += 1
                
                # Show first error immediately
                if len(errors) == 1:
                    print(f"  ❌ First error: {error_msg}")
    
    if errors and len(errors) <= 5:
        print(f"\n  ⚠️  Errors encountered:")
        for err in errors[:5]:
            print(f"     - {err}")
        if len(errors) > 5:
            print(f"     ... and {len(errors) - 5} more errors")
    
    return inserted, updated


def download_options_for_symbol(
    symbol: str,
    date: Optional[str] = None,
    config: Optional[DatabaseConfig] = None
) -> Tuple[int, int, Optional[str]]:
    """
    Download options data for a single symbol.
    
    Args:
        symbol: Stock symbol
        date: Specific date (YYYY-MM-DD)
        config: Database configuration
    
    Returns:
        Tuple of (inserted_count, updated_count, error_message)
    """
    print(f"\n[{symbol}] Processing options chain...")
    
    # Fetch from API
    df, error = fetch_historical_options(symbol, date)
    
    if error:
        print(f"  ❌ Error: {error}")
        return 0, 0, error
    
    if df is None or df.empty:
        print(f"  ⚠️  No data returned")
        return 0, 0, "No data returned"
    
    # Insert into database
    print(f"  💾 Inserting {len(df)} contracts into database...")
    inserted, updated = insert_options_data(df, config)
    
    print(f"  ✅ Inserted: {inserted}, Updated: {updated}")
    
    return inserted, updated, None


def download_options_for_multiple_symbols(
    symbols: List[str],
    date: Optional[str] = None,
    config: Optional[DatabaseConfig] = None
) -> dict:
    """
    Download options data for multiple symbols.
    
    Args:
        symbols: List of stock symbols
        date: Specific date (YYYY-MM-DD)
        config: Database configuration
    
    Returns:
        Statistics dictionary
    """
    print(f"\n{'='*70}")
    print(f"📊 ALPHA VANTAGE - HISTORICAL OPTIONS DATA")
    print(f"{'='*70}")
    print(f"Symbols: {', '.join(symbols)}")
    if date:
        print(f"Date: {date}")
    else:
        print(f"Date: Latest trading session")
    print(f"{'='*70}\n")
    
    stats = {
        'total': len(symbols),
        'success': 0,
        'failed': 0,
        'total_inserted': 0,
        'total_updated': 0,
        'total_contracts': 0
    }
    
    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol}")
        
        inserted, updated, error = download_options_for_symbol(symbol, date, config)
        
        if error:
            stats['failed'] += 1
        else:
            stats['success'] += 1
            stats['total_inserted'] += inserted
            stats['total_updated'] += updated
            stats['total_contracts'] += (inserted + updated)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 DOWNLOAD COMPLETE")
    print(f"{'='*70}")
    print(f"Total symbols: {stats['total']}")
    print(f"✅ Success: {stats['success']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"📊 Total contracts: {stats['total_contracts']:,}")
    print(f"   Inserted: {stats['total_inserted']:,}")
    print(f"   Updated: {stats['total_updated']:,}")
    print(f"{'='*70}\n")
    
    return stats


def download_interactive():
    """Interactive mode - prompts user for inputs."""
    print("\n" + "="*70)
    print("📊 ALPHA VANTAGE - HISTORICAL OPTIONS DATA")
    print("="*70 + "\n")
    
    print("This downloads historical options chains including:")
    print("  • Pricing: last, mark, bid/ask with sizes")
    print("  • Greeks: delta, gamma, theta, vega, rho")
    print("  • Implied Volatility (IV)")
    print("  • Volume & Open Interest")
    print("\nPress Ctrl+C at any time to cancel.\n")
    
    # Get symbol(s) with retry loop
    while True:
        symbol_input = input("Enter stock symbol(s) (comma-separated, e.g., AAPL, SPY): ").strip()
        if symbol_input:
            break
        print("⚠️  Please enter at least one symbol, or press Ctrl+C to cancel.\n")
    
    symbols = [s.strip().upper() for s in symbol_input.replace(',', ' ').split()]
    
    # Get date (optional) with validation
    print("\nDate (optional):")
    print("  Leave blank for most recent trading session")
    print("  Or enter specific date YYYY-MM-DD (available from 2008-01-01)")
    
    date = None
    while True:
        date_input = input("Date [optional]: ").strip()
        
        if not date_input:
            # User pressed Enter - use latest
            date = None
            break
        
        # Validate date format
        try:
            datetime.strptime(date_input, '%Y-%m-%d')
            date = date_input
            break
        except ValueError:
            print("⚠️  Invalid date format. Please use YYYY-MM-DD or leave blank.\n")
    
    # Download
    print()
    stats = download_options_for_multiple_symbols(symbols, date)
    
    if stats['failed'] > 0:
        sys.exit(1)


def main():
    """Main entry point with CLI and interactive modes."""
    parser = argparse.ArgumentParser(
        description='Download historical options data from Alpha Vantage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python -m data.alphavantage.options.historical
  
  # Latest options chain
  python -m data.alphavantage.options.historical --symbol AAPL
  
  # Specific date
  python -m data.alphavantage.options.historical --symbol AAPL --date 2025-10-15
  
  # Multiple symbols
  python -m data.alphavantage.options.historical --symbols AAPL MSFT TSLA
        """
    )
    
    parser.add_argument('--symbol', help='Single symbol to download')
    parser.add_argument('--symbols', nargs='+', help='Multiple symbols')
    parser.add_argument('--date', help='Specific date (YYYY-MM-DD, from 2008-01-01)')
    
    args = parser.parse_args()
    
    # If no arguments, use interactive mode
    if not args.symbol and not args.symbols:
        download_interactive()
        return
    
    # CLI mode
    symbols = [args.symbol] if args.symbol else args.symbols
    
    try:
        stats = download_options_for_multiple_symbols(symbols, args.date)
        
        if stats['failed'] > 0:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

