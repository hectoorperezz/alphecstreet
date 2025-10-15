# Data Collection Module

Este módulo maneja la descarga y almacenamiento de datos de mercado en TimescaleDB.

## 📁 Directory Structure

```
data/
├── database.py              # Core database utilities (shared)
├── yfinance/               # Yahoo Finance data provider
│   ├── download_sp500_yfinance.py
│   ├── download_indices.py
│   ├── add_tickers.py
│   ├── update_daily.py
│   └── README.md           # yfinance-specific docs
├── alphavantage/           # Alpha Vantage provider (PRODUCTION READY)
│   ├── core/              # Shared API client
│   ├── equities/          # Stock data (intraday, daily)
│   ├── options/           # Options with Greeks + IV
│   ├── docs/              # Documentation
│   └── README.md
└── README.md               # This file
```

## 🔌 Data Providers

### Alpha Vantage (🌟 Recommended - Production Ready)
Professional-grade data with excellent reliability:
- **Intraday**: 1min to 60min OHLCV (20+ years historical)
- **Options**: Historical chains with Greeks and IV (from 2008)
- **Rate limits**: 25 calls/day, 5 calls/minute (free tier)
- **See**: [`alphavantage/README.md`](./alphavantage/README.md)

### yfinance (Active, Daily Data)
Best for bulk daily data downloads:
- **Daily OHLCV**: Unlimited downloads
- **S&P 500 constituents**: Automatic tracking
- **Benchmark indices**: SPY, QQQ, etc.
- **See**: [`yfinance/README.md`](./yfinance/README.md)
- **Note**: Use for daily data; Alpha Vantage for intraday/options

## 🗄️ Base de Datos

### Configuración Inicial

1. **Levantar TimescaleDB con Docker:**
   ```bash
   cd infrastructure/database
   docker-compose up -d
   ```

2. **Verificar que está corriendo:**
   ```bash
   docker-compose ps
   ```

3. **Probar conexión:**
   ```bash
   python -m data.database
   ```

### Acceso a la Base de Datos

**PostgreSQL directamente:**
```bash
docker exec -it alphecstreet_timescaledb psql -U alphecstreet_user -d alphecstreet
```

**pgAdmin (interfaz web):**
- URL: http://localhost:5050
- Email: `admin@alphecstreet.local`
- Password: `admin`

**Credenciales de la base de datos:**
- Host: `localhost`
- Port: `5432`
- Database: `alphecstreet`
- User: `alphecstreet_user`
- Password: `alphecstreet_dev_2024`

## 📥 Descargar Datos

### 1. Actualizar Constituyentes del S&P 500

```bash
python -m data.yfinance.download_sp500_yfinance --update-constituents
```

Esto descarga la lista actual del S&P 500 desde Wikipedia y la guarda en la tabla `sp500_constituents`.

### 2. Descargar Datos Históricos Completos

**Todos los símbolos desde 2015:**
```bash
python -m data.yfinance.download_sp500_yfinance --update-constituents --start-date 2015-01-01
```

**Rango de fechas personalizado:**
```bash
python -m data.yfinance.download_sp500_yfinance --start-date 2020-01-01 --end-date 2023-12-31
```

**Un símbolo específico:**
```bash
python -m data.yfinance.download_sp500_yfinance --symbol AAPL --start-date 2020-01-01
```

**Saltar símbolos que ya tienen datos:**
```bash
python -m data.yfinance.download_sp500_yfinance --skip-existing --start-date 2015-01-01
```

### 3. Actualización Diaria

Para actualizar los datos con la información más reciente:

```bash
python -m data.yfinance.update_daily
```

Este script:
- Descarga los últimos 5 días de datos (para capturar datos perdidos por fines de semana/festivos)
- Actualiza todos los símbolos activos del S&P 500
- Evita duplicados (usa `ON CONFLICT DO UPDATE`)

**Personalizar días hacia atrás:**
```bash
python -m data.yfinance.update_daily --days-back 10
```

### 4. Descargar Índices de Benchmark

```bash
# Descargar todos los índices
python -m data.yfinance.download_indices --start-date 2020-01-01

# Actualización diaria
python -m data.yfinance.download_indices --daily-update
```

### 5. Agregar Tickers Personalizados

```bash
# Modo interactivo
python -m data.yfinance.add_tickers

# Línea de comandos
python -m data.yfinance.add_tickers --tickers AAPL MSFT TSLA
```

## 🔍 Queries Útiles

### Python

```python
from data.database import query_to_dataframe

# Obtener datos de AAPL
df = query_to_dataframe("""
    SELECT * FROM market_data_daily 
    WHERE symbol = 'AAPL' 
    ORDER BY "time" DESC 
    LIMIT 100
""")

# Usar funciones SQL personalizadas
returns = query_to_dataframe("""
    SELECT * FROM get_returns('AAPL', '2024-01-01', '2024-12-31')
""")

stats = query_to_dataframe("""
    SELECT * FROM get_price_stats('AAPL', 30)
""")
```

### SQL (en psql)

```sql
-- Ver últimos precios
SELECT * FROM latest_prices LIMIT 10;

-- Cobertura de datos por símbolo
SELECT * FROM data_coverage ORDER BY total_bars DESC LIMIT 10;

-- Resumen por sector
SELECT * FROM sector_summary;

-- Datos semanales (continuous aggregate)
SELECT * FROM market_data_weekly 
WHERE symbol = 'AAPL' 
ORDER BY "time" DESC 
LIMIT 10;

-- Datos mensuales
SELECT * FROM market_data_monthly 
WHERE symbol = 'AAPL' 
ORDER BY "time" DESC 
LIMIT 10;

-- Log de descargas
SELECT * FROM download_log ORDER BY timestamp DESC LIMIT 20;

-- Retornos diarios
SELECT * FROM get_returns('AAPL', '2024-01-01', '2024-12-31');

-- Estadísticas de los últimos 30 días
SELECT * FROM get_price_stats('AAPL', 30);
```

## 📊 Estructura de Tablas

### `market_data_daily`
Datos OHLCV diarios con ajustes por splits/dividendos.

```sql
CREATE TABLE market_data_daily (
    "time" DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DECIMAL(18, 6) NOT NULL,
    high DECIMAL(18, 6) NOT NULL,
    low DECIMAL(18, 6) NOT NULL,
    close DECIMAL(18, 6) NOT NULL,
    volume BIGINT NOT NULL,
    adj_close DECIMAL(18, 6) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY ("time", symbol)
);
```

**Features:**
- ✅ Hypertable de TimescaleDB (optimizada para series de tiempo)
- ✅ Compresión automática de datos > 30 días
- ✅ Particionado mensual para queries rápidas

### `sp500_constituents`
Lista de acciones en el S&P 500.

```sql
CREATE TABLE sp500_constituents (
    symbol VARCHAR(20) PRIMARY KEY,
    company_name VARCHAR(200),
    sector VARCHAR(100),
    sub_industry VARCHAR(100),
    cik VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    last_downloaded TIMESTAMPTZ,
    download_status VARCHAR(20) DEFAULT 'pending',
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### `download_log`
Registro de todas las descargas.

```sql
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
```

## 🔄 Continuous Aggregates

TimescaleDB mantiene automáticamente vistas materializadas actualizadas:

- **`market_data_weekly`**: Agregación semanal (OHLCV)
- **`market_data_monthly`**: Agregación mensual (OHLCV)

Estas se actualizan automáticamente cada día.

## 🛠️ Comandos de Mantenimiento

### Parar la base de datos
```bash
cd infrastructure/database
docker-compose down
```

### Reiniciar
```bash
docker-compose restart
```

### Ver logs
```bash
docker-compose logs -f timescaledb
```

### Backup
```bash
docker exec alphecstreet_timescaledb pg_dump -U alphecstreet_user alphecstreet > backup_$(date +%Y%m%d).sql
```

### Restaurar backup
```bash
cat backup_20241008.sql | docker exec -i alphecstreet_timescaledb psql -U alphecstreet_user -d alphecstreet
```

### Limpiar todo (⚠️ BORRA TODOS LOS DATOS)
```bash
docker-compose down -v
rm -rf ../../data/postgres_data
mkdir -p ../../data/postgres_data
docker-compose up -d
```

## 📝 Ejemplo Completo

```bash
# 1. Levantar base de datos
cd infrastructure/database
docker-compose up -d

# 2. Volver a la raíz del proyecto
cd ../..

# 3. Probar conexión
python -m data.database

# 4. Descargar constituyentes y datos históricos
python -m data.yfinance.download_sp500_yfinance \
    --update-constituents \
    --start-date 2020-01-01

# 5. Verificar datos
docker exec alphecstreet_timescaledb psql -U alphecstreet_user -d alphecstreet -c "SELECT * FROM data_coverage LIMIT 10"

# 6. Configurar actualización diaria (añadir a crontab)
# 0 18 * * * cd /path/to/alphecstreet && python -m data.yfinance.update_daily
```

## 🐛 Troubleshooting

**Error: "Connection refused"**
- Asegúrate de que Docker esté corriendo: `docker-compose ps`
- Verifica que el puerto 5432 no esté ocupado: `lsof -i :5432`

**Error: "No module named 'data'"**
- Instala el paquete en modo editable: `pip install -e .`

**Algunos símbolos fallan al descargar**
- Es normal, algunos símbolos pueden no tener datos en yfinance
- Revisa `download_log` para ver errores específicos

**La descarga es muy lenta**
- yfinance tiene límites de tasa
- Para 500 símbolos con 10 años de datos, espera 30-60 minutos

**pgAdmin no inicia**
- Es opcional, solo para interfaz visual
- Puedes usar `psql` directamente sin problemas
