-- ============================================
-- Alphec Street - Market Data Schema
-- Source: yfinance (daily data only)
-- Universe: S&P 500
-- ============================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================
-- TABLA PRINCIPAL: market_data_daily
-- ============================================
CREATE TABLE market_data_daily (
    "time" DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    
    -- OHLCV
    open DECIMAL(18, 6) NOT NULL,
    high DECIMAL(18, 6) NOT NULL,
    low DECIMAL(18, 6) NOT NULL,
    close DECIMAL(18, 6) NOT NULL,
    volume BIGINT NOT NULL,
    
    -- Precio ajustado por splits/dividendos
    adj_close DECIMAL(18, 6) NOT NULL,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY ("time", symbol)
);

-- Convertir a hypertable de TimescaleDB
SELECT create_hypertable('market_data_daily', 'time', 
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Índices para queries rápidas
CREATE INDEX idx_market_data_daily_symbol ON market_data_daily (symbol, "time" DESC);
CREATE INDEX idx_market_data_daily_time ON market_data_daily ("time" DESC);

-- Compresión automática (datos > 30 días)
ALTER TABLE market_data_daily SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('market_data_daily', INTERVAL '30 days');

-- ============================================
-- TABLA: sp500_constituents
-- ============================================
CREATE TABLE sp500_constituents (
    symbol VARCHAR(20) PRIMARY KEY,
    company_name VARCHAR(200),
    sector VARCHAR(100),
    sub_industry VARCHAR(100),
    
    -- Metadata
    cik VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Control de descarga
    last_downloaded TIMESTAMPTZ,
    download_status VARCHAR(20) DEFAULT 'pending',
    
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sp500_sector ON sp500_constituents (sector);
CREATE INDEX idx_sp500_active ON sp500_constituents (is_active);

-- ============================================
-- TABLA: download_log
-- ============================================
CREATE TABLE download_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    batch_id VARCHAR(50),
    
    symbol VARCHAR(20),
    start_date DATE,
    end_date DATE,
    bars_downloaded INTEGER,
    
    status VARCHAR(20),  -- SUCCESS, ERROR, SKIPPED
    error_message TEXT,
    duration_seconds DECIMAL(10, 3)
);

CREATE INDEX idx_download_log_timestamp ON download_log (timestamp DESC);
CREATE INDEX idx_download_log_symbol ON download_log (symbol, timestamp DESC);
CREATE INDEX idx_download_log_batch ON download_log (batch_id);

-- ============================================
-- CONTINUOUS AGGREGATES (agregaciones automáticas)
-- ============================================

-- Semanal
CREATE MATERIALIZED VIEW market_data_weekly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 week', "time") AS "time",
    symbol,
    FIRST(open, "time") as open,
    MAX(high) as high,
    MIN(low) as low,
    LAST(close, "time") as close,
    LAST(adj_close, "time") as adj_close,
    SUM(volume) as volume
FROM market_data_daily
GROUP BY time_bucket('1 week', "time"), symbol;

SELECT add_continuous_aggregate_policy('market_data_weekly',
    start_offset => INTERVAL '3 weeks',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- Mensual
CREATE MATERIALIZED VIEW market_data_monthly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 month', "time") AS "time",
    symbol,
    FIRST(open, "time") as open,
    MAX(high) as high,
    MIN(low) as low,
    LAST(close, "time") as close,
    LAST(adj_close, "time") as adj_close,
    SUM(volume) as volume
FROM market_data_daily
GROUP BY time_bucket('1 month', "time"), symbol;

SELECT add_continuous_aggregate_policy('market_data_monthly',
    start_offset => INTERVAL '3 months',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

-- ============================================
-- VISTAS ÚTILES
-- ============================================

-- Últimos precios
CREATE VIEW latest_prices AS
SELECT DISTINCT ON (symbol)
    symbol,
    "time",
    close,
    adj_close,
    volume
FROM market_data_daily
ORDER BY symbol, "time" DESC;

-- Cobertura de datos
CREATE VIEW data_coverage AS
SELECT
    m.symbol,
    s.company_name,
    s.sector,
    MIN(m."time") as first_date,
    MAX(m."time") as last_date,
    COUNT(*) as total_bars,
    MAX(m."time")::date - MIN(m."time")::date as days_coverage
FROM market_data_daily m
JOIN sp500_constituents s ON m.symbol = s.symbol
GROUP BY m.symbol, s.company_name, s.sector
ORDER BY m.symbol;

-- Resumen por sector
CREATE VIEW sector_summary AS
SELECT
    s.sector,
    COUNT(DISTINCT s.symbol) as num_stocks,
    COUNT(DISTINCT m.symbol) as stocks_with_data,
    MIN(m."time") as earliest_data,
    MAX(m."time") as latest_data
FROM sp500_constituents s
LEFT JOIN market_data_daily m ON s.symbol = m.symbol
WHERE s.is_active = TRUE
GROUP BY s.sector
ORDER BY num_stocks DESC;

-- ============================================
-- FUNCIONES ÚTILES
-- ============================================

-- Obtener OHLCV
CREATE OR REPLACE FUNCTION get_ohlcv(
    p_symbol VARCHAR,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    "time" DATE,
    open DECIMAL,
    high DECIMAL,
    low DECIMAL,
    close DECIMAL,
    adj_close DECIMAL,
    volume BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT m."time", m.open, m.high, m.low, m.close, m.adj_close, m.volume
    FROM market_data_daily m
    WHERE m.symbol = p_symbol
      AND m."time" >= p_start_date
      AND m."time" <= p_end_date
    ORDER BY m."time";
END;
$$ LANGUAGE plpgsql STABLE;

-- Calcular retornos
CREATE OR REPLACE FUNCTION get_returns(
    p_symbol VARCHAR,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    date DATE,
    close_price DECIMAL,
    daily_return DECIMAL,
    cumulative_return DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    WITH prices AS (
        SELECT
            "time",
            adj_close,
            LAG(adj_close) OVER (ORDER BY "time") as prev_close
        FROM market_data_daily
        WHERE symbol = p_symbol
          AND "time" >= p_start_date
          AND "time" <= p_end_date
        ORDER BY "time"
    )
    SELECT
        "time"::date,
        adj_close,
        ((adj_close - prev_close) / prev_close * 100)::DECIMAL(10,4) as daily_return,
        ((adj_close / FIRST_VALUE(adj_close) OVER (ORDER BY "time") - 1) * 100)::DECIMAL(10,4) as cumulative_return
    FROM prices
    WHERE prev_close IS NOT NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- Estadísticas básicas
CREATE OR REPLACE FUNCTION get_price_stats(
    p_symbol VARCHAR,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    symbol VARCHAR,
    current_price DECIMAL,
    avg_price DECIMAL,
    min_price DECIMAL,
    max_price DECIMAL,
    volatility DECIMAL,
    avg_volume BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p_symbol::VARCHAR,
        LAST(adj_close, "time") as current_price,
        AVG(adj_close)::DECIMAL(18,6) as avg_price,
        MIN(adj_close) as min_price,
        MAX(adj_close) as max_price,
        STDDEV(adj_close)::DECIMAL(18,6) as volatility,
        AVG(volume)::BIGINT as avg_volume
    FROM market_data_daily
    WHERE symbol = p_symbol
      AND "time" >= CURRENT_DATE - p_days;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- TABLA: benchmark_indices
-- Track benchmark indices/ETFs for performance comparison
-- ============================================
CREATE TABLE benchmark_indices (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 'equity', 'bond', 'commodity', 'volatility'
    description TEXT,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    last_downloaded TIMESTAMPTZ,
    download_status VARCHAR(20) DEFAULT 'pending',
    
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_benchmark_category ON benchmark_indices (category);
CREATE INDEX idx_benchmark_active ON benchmark_indices (is_active);

-- Insert common benchmark indices
INSERT INTO benchmark_indices (symbol, name, category, description) VALUES
    -- Major Market Indices
    ('SPY', 'SPDR S&P 500 ETF', 'equity', 'S&P 500 benchmark'),
    ('QQQ', 'Invesco QQQ ETF', 'equity', 'NASDAQ-100 benchmark'),
    ('DIA', 'SPDR Dow Jones ETF', 'equity', 'Dow Jones benchmark'),
    ('IWM', 'iShares Russell 2000 ETF', 'equity', 'Small cap benchmark'),
    ('VTI', 'Vanguard Total Stock Market ETF', 'equity', 'Total US market'),
    ('^GSPC', 'S&P 500 Index', 'equity', 'S&P 500 Index'),
    ('^IXIC', 'NASDAQ Composite', 'equity', 'NASDAQ Composite'),
    ('^DJI', 'Dow Jones Industrial Average', 'equity', 'DJIA'),
    
    -- Sector ETFs
    ('XLK', 'Technology Select Sector SPDR', 'equity', 'Technology sector'),
    ('XLF', 'Financial Select Sector SPDR', 'equity', 'Financial sector'),
    ('XLE', 'Energy Select Sector SPDR', 'equity', 'Energy sector'),
    
    -- International
    ('EFA', 'iShares MSCI EAFE ETF', 'equity', 'Developed markets ex-US'),
    ('EEM', 'iShares MSCI Emerging Markets', 'equity', 'Emerging markets'),
    
    -- Fixed Income
    ('AGG', 'iShares Core US Aggregate Bond', 'bond', 'US aggregate bonds'),
    ('TLT', 'iShares 20+ Year Treasury Bond', 'bond', 'Long-term treasuries'),
    
    -- Commodities
    ('GLD', 'SPDR Gold Shares', 'commodity', 'Gold'),
    
    -- Volatility
    ('^VIX', 'CBOE Volatility Index', 'volatility', 'Market volatility')
ON CONFLICT (symbol) DO NOTHING;

-- ============================================
-- FUNCIÓN: Comparar stock vs benchmark
-- ============================================
CREATE OR REPLACE FUNCTION compare_to_benchmark(
    p_symbol VARCHAR,
    p_benchmark VARCHAR DEFAULT 'SPY',
    p_start_date DATE DEFAULT CURRENT_DATE - INTERVAL '1 year',
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    date DATE,
    stock_return_pct DECIMAL,
    benchmark_return_pct DECIMAL,
    alpha_pct DECIMAL,
    stock_cumulative_pct DECIMAL,
    benchmark_cumulative_pct DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    WITH stock_data AS (
        SELECT
            "time",
            adj_close,
            FIRST_VALUE(adj_close) OVER (ORDER BY "time") as start_price
        FROM market_data_daily
        WHERE symbol = p_symbol
          AND "time" >= p_start_date
          AND "time" <= p_end_date
    ),
    benchmark_data AS (
        SELECT
            "time",
            adj_close,
            FIRST_VALUE(adj_close) OVER (ORDER BY "time") as start_price
        FROM market_data_daily
        WHERE symbol = p_benchmark
          AND "time" >= p_start_date
          AND "time" <= p_end_date
    )
    SELECT
        s."time"::date,
        COALESCE(((s.adj_close - LAG(s.adj_close) OVER (ORDER BY s."time")) / 
         NULLIF(LAG(s.adj_close) OVER (ORDER BY s."time"), 0) * 100), 0)::DECIMAL(10,4) as stock_return,
        COALESCE(((b.adj_close - LAG(b.adj_close) OVER (ORDER BY s."time")) / 
         NULLIF(LAG(b.adj_close) OVER (ORDER BY s."time"), 0) * 100), 0)::DECIMAL(10,4) as benchmark_return,
        COALESCE((((s.adj_close - LAG(s.adj_close) OVER (ORDER BY s."time")) / 
         NULLIF(LAG(s.adj_close) OVER (ORDER BY s."time"), 0)) -
         ((b.adj_close - LAG(b.adj_close) OVER (ORDER BY s."time")) / 
         NULLIF(LAG(b.adj_close) OVER (ORDER BY s."time"), 0))) * 100, 0)::DECIMAL(10,4) as alpha,
        ((s.adj_close / NULLIF(s.start_price, 0) - 1) * 100)::DECIMAL(10,4) as stock_cumulative,
        ((b.adj_close / NULLIF(b.start_price, 0) - 1) * 100)::DECIMAL(10,4) as benchmark_cumulative
    FROM stock_data s
    JOIN benchmark_data b ON s."time" = b."time";
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- Grants
-- ============================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO alphecstreet_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO alphecstreet_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO alphecstreet_user;

-- ============================================
-- Confirmación
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ Market Data schema initialized (yfinance daily)';
    RAISE NOTICE '📊 Ready to download S&P 500';
    RAISE NOTICE '📈 Benchmark indices: 17 indices ready';
    RAISE NOTICE '🗜️  Compression policy: 30 days';
    RAISE NOTICE '📊 Aggregates: weekly, monthly';
    RAISE NOTICE '🎯 Benchmarking: compare_to_benchmark() function ready';
END $$;

