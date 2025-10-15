-- ============================================
-- Alphec Street - Intraday Market Data Schema
-- Source: Alpha Vantage (1min, 5min, 15min, 30min, 60min)
-- ============================================

-- ============================================
-- TABLA: market_data_intraday
-- Stores intraday OHLCV data (1min, 5min, etc.)
-- ============================================
CREATE TABLE IF NOT EXISTS market_data_intraday (
    "time" TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,  -- '1min', '5min', '15min', '30min', '60min'
    
    -- OHLCV
    open DECIMAL(18, 6) NOT NULL,
    high DECIMAL(18, 6) NOT NULL,
    low DECIMAL(18, 6) NOT NULL,
    close DECIMAL(18, 6) NOT NULL,
    volume BIGINT NOT NULL,
    
    -- Metadata
    data_source VARCHAR(50) DEFAULT 'alphavantage',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY ("time", symbol, interval)
);

-- Convert to TimescaleDB hypertable
-- Use 1 day chunks for intraday data (better for range queries)
SELECT create_hypertable('market_data_intraday', 'time', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_intraday_symbol_time 
    ON market_data_intraday (symbol, interval, "time" DESC);

CREATE INDEX IF NOT EXISTS idx_intraday_interval 
    ON market_data_intraday (interval, "time" DESC);

CREATE INDEX IF NOT EXISTS idx_intraday_symbol_interval 
    ON market_data_intraday (symbol, interval);

-- Compression policy (compress data > 7 days old)
ALTER TABLE market_data_intraday SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, interval',
    timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('market_data_intraday', INTERVAL '7 days');

-- ============================================
-- VIEW: Latest intraday prices
-- ============================================
CREATE OR REPLACE VIEW latest_intraday_prices AS
SELECT DISTINCT ON (symbol, interval)
    symbol,
    interval,
    "time",
    close as last_price,
    volume
FROM market_data_intraday
ORDER BY symbol, interval, "time" DESC;

-- ============================================
-- VIEW: Intraday data coverage
-- ============================================
CREATE OR REPLACE VIEW intraday_data_coverage AS
SELECT 
    symbol,
    interval,
    MIN("time") as first_bar,
    MAX("time") as last_bar,
    COUNT(*) as total_bars,
    data_source
FROM market_data_intraday
GROUP BY symbol, interval, data_source
ORDER BY symbol, interval;

-- ============================================
-- CONTINUOUS AGGREGATE: Hourly OHLCV
-- (Aggregates 1min data into hourly bars)
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', "time") AS "time",
    symbol,
    FIRST(open, "time") as open,
    MAX(high) as high,
    MIN(low) as low,
    LAST(close, "time") as close,
    SUM(volume) as volume,
    COUNT(*) as bars_aggregated
FROM market_data_intraday
WHERE interval = '1min'
GROUP BY time_bucket('1 hour', "time"), symbol
WITH NO DATA;

-- Refresh policy: Update hourly view every 15 minutes
SELECT add_continuous_aggregate_policy('market_data_hourly',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => TRUE
);

-- ============================================
-- FUNCTION: Get intraday bars for symbol
-- ============================================
CREATE OR REPLACE FUNCTION get_intraday_bars(
    p_symbol VARCHAR,
    p_interval VARCHAR DEFAULT '1min',
    p_start_time TIMESTAMPTZ DEFAULT NOW() - INTERVAL '1 day',
    p_end_time TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    bar_time TIMESTAMPTZ,
    bar_open DECIMAL,
    bar_high DECIMAL,
    bar_low DECIMAL,
    bar_close DECIMAL,
    bar_volume BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        "time" as bar_time,
        market_data_intraday.open as bar_open,
        market_data_intraday.high as bar_high,
        market_data_intraday.low as bar_low,
        market_data_intraday.close as bar_close,
        market_data_intraday.volume as bar_volume
    FROM market_data_intraday
    WHERE symbol = p_symbol
      AND interval = p_interval
      AND "time" >= p_start_time
      AND "time" <= p_end_time
    ORDER BY "time";
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- FUNCTION: Get intraday statistics
-- ============================================
CREATE OR REPLACE FUNCTION get_intraday_stats(
    p_symbol VARCHAR,
    p_interval VARCHAR DEFAULT '1min',
    p_hours INT DEFAULT 24
)
RETURNS TABLE (
    ticker_symbol VARCHAR,
    time_interval VARCHAR,
    bars_count BIGINT,
    price_open DECIMAL,
    price_high DECIMAL,
    price_low DECIMAL,
    price_close DECIMAL,
    volume_total BIGINT,
    price_change_pct DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    WITH stats AS (
        SELECT 
            FIRST(market_data_intraday.open, "time") as first_open,
            MAX(market_data_intraday.high) as max_high,
            MIN(market_data_intraday.low) as min_low,
            LAST(market_data_intraday.close, "time") as last_close,
            SUM(market_data_intraday.volume) as total_volume,
            COUNT(*) as bar_count
        FROM market_data_intraday
        WHERE market_data_intraday.symbol = p_symbol
          AND market_data_intraday.interval = p_interval
          AND "time" >= NOW() - (p_hours || ' hours')::INTERVAL
    )
    SELECT 
        p_symbol::VARCHAR,
        p_interval::VARCHAR,
        bar_count,
        first_open,
        max_high,
        min_low,
        last_close,
        total_volume,
        CASE 
            WHEN first_open > 0 THEN ((last_close - first_open) / first_open * 100)::DECIMAL(10,4)
            ELSE 0::DECIMAL(10,4)
        END as change_pct
    FROM stats;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- Comments
-- ============================================
COMMENT ON TABLE market_data_intraday IS 
    'Intraday OHLCV data from Alpha Vantage (1min, 5min, 15min, 30min, 60min intervals)';

COMMENT ON COLUMN market_data_intraday.interval IS 
    'Time interval: 1min, 5min, 15min, 30min, 60min';

COMMENT ON VIEW intraday_data_coverage IS 
    'Summary of available intraday data by symbol and interval';

COMMENT ON MATERIALIZED VIEW market_data_hourly IS 
    'Continuous aggregate: 1-minute bars aggregated into hourly OHLCV';

