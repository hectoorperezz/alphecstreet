-- ============================================
-- Alphec Street - Options Data Schema
-- Source: Alpha Vantage HISTORICAL_OPTIONS
-- Coverage: 15+ years (from 2008-01-01)
-- ============================================

-- ============================================
-- TABLE: options_data_historical
-- Stores historical options chains with Greeks and IV
-- ============================================
CREATE TABLE IF NOT EXISTS options_data_historical (
    date DATE NOT NULL,
    contract_id VARCHAR(50) NOT NULL,
    
    -- Contract details
    symbol VARCHAR(20) NOT NULL,
    expiration DATE NOT NULL,
    strike DECIMAL(18, 6) NOT NULL,
    type VARCHAR(4) NOT NULL,  -- 'call' or 'put'
    
    -- Pricing
    last DECIMAL(18, 6),       -- Last traded price
    mark DECIMAL(18, 6),       -- Mark price (midpoint)
    bid DECIMAL(18, 6),
    bid_size INTEGER,
    ask DECIMAL(18, 6),
    ask_size INTEGER,
    
    -- Volume & Interest
    volume BIGINT,
    open_interest BIGINT,
    
    -- Greeks (provided by Alpha Vantage)
    implied_volatility DECIMAL(10, 6),
    delta DECIMAL(10, 6),
    gamma DECIMAL(10, 6),
    theta DECIMAL(10, 6),
    vega DECIMAL(10, 6),
    rho DECIMAL(10, 6),
    
    -- Metadata
    data_source VARCHAR(50) DEFAULT 'alphavantage',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (date, contract_id)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('options_data_historical', 'date',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_options_symbol_exp 
    ON options_data_historical (symbol, expiration, date DESC);

CREATE INDEX IF NOT EXISTS idx_options_expiration 
    ON options_data_historical (expiration, date DESC);

CREATE INDEX IF NOT EXISTS idx_options_type_strike 
    ON options_data_historical (type, strike, date DESC);

CREATE INDEX IF NOT EXISTS idx_options_contract 
    ON options_data_historical (contract_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_options_symbol_date 
    ON options_data_historical (symbol, date DESC);

-- Compression policy (compress data > 30 days old)
ALTER TABLE options_data_historical SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, contract_id',
    timescaledb.compress_orderby = 'date DESC'
);

SELECT add_compression_policy('options_data_historical', INTERVAL '30 days', if_not_exists => TRUE);

-- ============================================
-- VIEW: Latest option chain
-- ============================================
CREATE OR REPLACE VIEW latest_options_chain AS
SELECT DISTINCT ON (contract_id)
    contract_id,
    symbol,
    expiration,
    strike,
    type,
    last,
    mark,
    bid,
    ask,
    volume,
    open_interest,
    delta,
    gamma,
    theta,
    vega,
    rho,
    implied_volatility,
    date
FROM options_data_historical
ORDER BY contract_id, date DESC;

-- ============================================
-- VIEW: Options data coverage
-- ============================================
CREATE OR REPLACE VIEW options_data_coverage AS
SELECT 
    symbol,
    MIN(date) as first_date,
    MAX(date) as last_date,
    COUNT(DISTINCT date) as trading_days,
    COUNT(*) as total_contracts,
    COUNT(DISTINCT contract_id) as unique_contracts,
    COUNT(DISTINCT expiration) as unique_expirations
FROM options_data_historical
GROUP BY symbol
ORDER BY symbol;

-- ============================================
-- FUNCTION: Get option chain for specific date
-- ============================================
CREATE OR REPLACE FUNCTION get_option_chain(
    p_symbol VARCHAR,
    p_date DATE DEFAULT CURRENT_DATE,
    p_expiration_min DATE DEFAULT NULL,
    p_expiration_max DATE DEFAULT NULL,
    p_option_type VARCHAR DEFAULT NULL  -- 'call', 'put', or NULL for both
)
RETURNS TABLE (
    contract_id VARCHAR,
    expiration DATE,
    strike DECIMAL,
    option_type VARCHAR,
    last DECIMAL,
    mark DECIMAL,
    bid DECIMAL,
    ask DECIMAL,
    volume BIGINT,
    open_interest BIGINT,
    iv DECIMAL,
    delta DECIMAL,
    gamma DECIMAL,
    theta DECIMAL,
    vega DECIMAL,
    rho DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        options_data_historical.contract_id,
        options_data_historical.expiration,
        options_data_historical.strike,
        options_data_historical.type,
        options_data_historical.last,
        options_data_historical.mark,
        options_data_historical.bid,
        options_data_historical.ask,
        options_data_historical.volume,
        options_data_historical.open_interest,
        options_data_historical.implied_volatility,
        options_data_historical.delta,
        options_data_historical.gamma,
        options_data_historical.theta,
        options_data_historical.vega,
        options_data_historical.rho
    FROM options_data_historical
    WHERE symbol = p_symbol
      AND date = p_date
      AND (p_expiration_min IS NULL OR expiration >= p_expiration_min)
      AND (p_expiration_max IS NULL OR expiration <= p_expiration_max)
      AND (p_option_type IS NULL OR type = p_option_type)
    ORDER BY expiration, strike;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- FUNCTION: Get options summary for symbol/date
-- ============================================
CREATE OR REPLACE FUNCTION get_options_summary(
    p_symbol VARCHAR,
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    total_contracts BIGINT,
    total_calls BIGINT,
    total_puts BIGINT,
    unique_expirations BIGINT,
    min_expiration DATE,
    max_expiration DATE,
    avg_iv_calls DECIMAL,
    avg_iv_puts DECIMAL,
    total_volume BIGINT,
    total_open_interest BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_contracts,
        COUNT(*) FILTER (WHERE type = 'call')::BIGINT as total_calls,
        COUNT(*) FILTER (WHERE type = 'put')::BIGINT as total_puts,
        COUNT(DISTINCT expiration)::BIGINT as unique_expirations,
        MIN(expiration) as min_expiration,
        MAX(expiration) as max_expiration,
        AVG(implied_volatility) FILTER (WHERE type = 'call') as avg_iv_calls,
        AVG(implied_volatility) FILTER (WHERE type = 'put') as avg_iv_puts,
        SUM(volume)::BIGINT as total_volume,
        SUM(open_interest)::BIGINT as total_open_interest
    FROM options_data_historical
    WHERE symbol = p_symbol
      AND date = p_date;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- Comments
-- ============================================
COMMENT ON TABLE options_data_historical IS 
    'Historical options chains from Alpha Vantage with Greeks and IV';

COMMENT ON COLUMN options_data_historical.last IS 
    'Last traded price';

COMMENT ON COLUMN options_data_historical.mark IS 
    'Mark price (midpoint between bid and ask)';

COMMENT ON COLUMN options_data_historical.implied_volatility IS 
    'Implied volatility (annualized)';

COMMENT ON VIEW latest_options_chain IS 
    'Most recent options chain for each contract';

COMMENT ON VIEW options_data_coverage IS 
    'Summary of available options data by symbol';

