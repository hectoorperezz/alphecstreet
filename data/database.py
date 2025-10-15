"""
Database connection and utility functions for TimescaleDB.
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd


class DatabaseConfig:
    """Configuration for database connection."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "alphecstreet",
        user: str = "alphecstreet_user",
        password: str = "alphecstreet_dev_2024",
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "alphecstreet"),
            user=os.getenv("DB_USER", "alphecstreet_user"),
            password=os.getenv("DB_PASSWORD", "alphecstreet_dev_2024"),
        )
    
    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return (
            f"host={self.host} port={self.port} dbname={self.database} "
            f"user={self.user} password={self.password}"
        )


@contextmanager
def get_db_connection(
    config: Optional[DatabaseConfig] = None
) -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager for database connections.
    
    Args:
        config: Database configuration. If None, uses default config.
    
    Yields:
        Active database connection
    
    Example:
        >>> with get_db_connection() as conn:
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT * FROM market_data_daily LIMIT 1")
    """
    if config is None:
        config = DatabaseConfig.from_env()
    
    conn = psycopg2.connect(config.connection_string)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_query(
    query: str,
    params: Optional[tuple] = None,
    config: Optional[DatabaseConfig] = None,
) -> list[dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries.
    
    Args:
        query: SQL query to execute
        params: Query parameters (optional)
        config: Database configuration (optional)
    
    Returns:
        List of dictionaries with query results
    
    Example:
        >>> results = execute_query("SELECT * FROM sp500_constituents WHERE sector = %s", ("Technology",))
        >>> for row in results:
        ...     print(row['symbol'], row['company_name'])
    """
    with get_db_connection(config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


def execute_command(
    command: str,
    params: Optional[tuple] = None,
    config: Optional[DatabaseConfig] = None,
) -> None:
    """
    Execute an INSERT/UPDATE/DELETE command.
    
    Args:
        command: SQL command to execute
        params: Command parameters (optional)
        config: Database configuration (optional)
    
    Example:
        >>> execute_command(
        ...     "INSERT INTO sp500_constituents (symbol, company_name) VALUES (%s, %s)",
        ...     ("AAPL", "Apple Inc.")
        ... )
    """
    with get_db_connection(config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(command, params)


def query_to_dataframe(
    query: str,
    params: Optional[tuple] = None,
    config: Optional[DatabaseConfig] = None,
) -> pd.DataFrame:
    """
    Execute query and return results as pandas DataFrame.
    
    Args:
        query: SQL query to execute
        params: Query parameters (optional)
        config: Database configuration (optional)
    
    Returns:
        DataFrame with query results
    
    Example:
        >>> df = query_to_dataframe(
        ...     "SELECT * FROM market_data_daily WHERE symbol = %s ORDER BY time",
        ...     ("AAPL",)
        ... )
        >>> print(df.head())
    """
    if config is None:
        config = DatabaseConfig.from_env()
    
    with get_db_connection(config) as conn:
        return pd.read_sql_query(query, conn, params=params)


def insert_dataframe(
    df: pd.DataFrame,
    table: str,
    config: Optional[DatabaseConfig] = None,
    if_exists: str = "append",
) -> int:
    """
    Insert pandas DataFrame into database table.
    
    Args:
        df: DataFrame to insert
        table: Target table name
        config: Database configuration (optional)
        if_exists: How to behave if table exists ('fail', 'replace', 'append')
    
    Returns:
        Number of rows inserted
    
    Example:
        >>> df = pd.DataFrame({
        ...     'time': ['2024-01-01'],
        ...     'symbol': ['AAPL'],
        ...     'open': [150.0],
        ...     'high': [155.0],
        ...     'low': [149.0],
        ...     'close': [154.0],
        ...     'volume': [1000000],
        ...     'adj_close': [154.0]
        ... })
        >>> rows = insert_dataframe(df, 'market_data_daily')
    """
    if config is None:
        config = DatabaseConfig.from_env()
    
    with get_db_connection(config) as conn:
        df.to_sql(table, conn, if_exists=if_exists, index=False)
        return len(df)


def test_connection(config: Optional[DatabaseConfig] = None) -> bool:
    """
    Test database connection.
    
    Args:
        config: Database configuration (optional)
    
    Returns:
        True if connection successful, False otherwise
    
    Example:
        >>> if test_connection():
        ...     print("Database is accessible!")
    """
    try:
        with get_db_connection(config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()[0] == 1
    except Exception as e:
        print(f"Connection failed: {e}")
        return False


def get_database_info(config: Optional[DatabaseConfig] = None) -> dict[str, Any]:
    """
    Get information about the database.
    
    Args:
        config: Database configuration (optional)
    
    Returns:
        Dictionary with database information
    
    Example:
        >>> info = get_database_info()
        >>> print(f"Tables: {info['tables']}")
        >>> print(f"Total rows in market_data_daily: {info['market_data_daily_count']}")
    """
    with get_db_connection(config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get table names
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            tables = [row['tablename'] for row in cursor.fetchall()]
            
            # Get row counts
            info = {"tables": tables}
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                info[f"{table}_count"] = cursor.fetchone()['count']
            
            # Get TimescaleDB version
            cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
            result = cursor.fetchone()
            info["timescaledb_version"] = result['extversion'] if result else None
            
            return info


if __name__ == "__main__":
    # Test connection
    print("Testing database connection...")
    
    if test_connection():
        print("✅ Connection successful!")
        
        info = get_database_info()
        print("\n📊 Database Information:")
        print(f"   TimescaleDB version: {info['timescaledb_version']}")
        print(f"   Tables: {', '.join(info['tables'])}")
        
        for table in info['tables']:
            count = info[f"{table}_count"]
            print(f"   {table}: {count} rows")
    else:
        print("❌ Connection failed!")
