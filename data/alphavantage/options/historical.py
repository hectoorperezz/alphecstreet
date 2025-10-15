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
    
    Args:
        df: DataFrame from fetch_historical_options()
        config: Database configuration
    
    Returns:
        Tuple of (inserted_count, updated_count)
    """
    if df.empty:
        return 0, 0
    
    inserted = 0
    updated = 0
    
    with get_db_connection(config) as conn:
        with conn.cursor() as cursor:
            for _, row in df.iterrows():
                # Convert values safely
                try:
                    cursor.execute("""
                        INSERT INTO options_data_historical 
                            (date, contract_id, symbol, expiration, strike, type,
                             last, mark, bid, bid_size, ask, ask_size,
                             volume, open_interest,
                             implied_volatility, delta, gamma, theta, vega, rho,
                             data_source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, 'alphavantage')
                        ON CONFLICT (date, contract_id)
                        DO UPDATE SET
                            last = EXCLUDED.last,
                            mark = EXCLUDED.mark,
                            bid = EXCLUDED.bid,
                            bid_size = EXCLUDED.bid_size,
                            ask = EXCLUDED.ask,
                            ask_size = EXCLUDED.ask_size,
                            volume = EXCLUDED.volume,
                            open_interest = EXCLUDED.open_interest,
                            implied_volatility = EXCLUDED.implied_volatility,
                            delta = EXCLUDED.delta,
                            gamma = EXCLUDED.gamma,
                            theta = EXCLUDED.theta,
                            vega = EXCLUDED.vega,
                            rho = EXCLUDED.rho,
                            updated_at = NOW()
                        RETURNING (xmax = 0) AS inserted
                    """, (
                        row.get('date'),
                        row.get('contractID'),
                        row.get('symbol'),
                        row.get('expiration'),
                        float(row['strike']) if row.get('strike') else None,
                        row.get('type'),
                        float(row['last']) if row.get('last') and row['last'] != '' else None,
                        float(row['mark']) if row.get('mark') and row['mark'] != '' else None,
                        float(row['bid']) if row.get('bid') and row['bid'] != '' else None,
                        int(row['bid_size']) if row.get('bid_size') and row['bid_size'] != '' else None,
                        float(row['ask']) if row.get('ask') and row['ask'] != '' else None,
                        int(row['ask_size']) if row.get('ask_size') and row['ask_size'] != '' else None,
                        int(row['volume']) if row.get('volume') and row['volume'] != '' else None,
                        int(row['open_interest']) if row.get('open_interest') and row['open_interest'] != '' else None,
                        float(row['implied_volatility']) if row.get('implied_volatility') and row['implied_volatility'] != '' else None,
                        float(row['delta']) if row.get('delta') and row['delta'] != '' else None,
                        float(row['gamma']) if row.get('gamma') and row['gamma'] != '' else None,
                        float(row['theta']) if row.get('theta') and row['theta'] != '' else None,
                        float(row['vega']) if row.get('vega') and row['vega'] != '' else None,
                        float(row['rho']) if row.get('rho') and row['rho'] != '' else None,
                    ))
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        inserted += 1
                    else:
                        updated += 1
                        
                except Exception as e:
                    print(f"  ⚠️  Skipping contract {row.get('contractID')}: {e}")
                    continue
    
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
    print()
    
    # Get symbol(s)
    symbol_input = input("Enter stock symbol(s) (comma-separated, e.g., AAPL, SPY): ").strip()
    if not symbol_input:
        print("❌ Symbol is required")
        sys.exit(1)
    
    symbols = [s.strip().upper() for s in symbol_input.replace(',', ' ').split()]
    
    # Get date (optional)
    print("\nDate (optional):")
    print("  Leave blank for most recent trading session")
    print("  Or enter specific date YYYY-MM-DD (available from 2008-01-01)")
    date = input("Date [optional]: ").strip() or None
    
    # Validate date format if provided
    if date:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    
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

