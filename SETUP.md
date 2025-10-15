# Development Environment Setup

## Prerequisites

- Python 3.11 or higher
- Git
- Interactive Brokers Trader Workstation (TWS) or IB Gateway installed
- IBKR account (paper trading account recommended for development)

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd alphecstreet
```

### 2. Create Virtual Environment

```bash
# Using venv (built-in)
python3.11 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Or using conda
conda create -n alphecstreet python=3.11
conda activate alphecstreet
```

### 3. Install Package and Dependencies

**Important**: You must install the package in editable mode for Python to find the modules.

```bash
# Install the package in editable mode (required)
pip install -e .

# For development (includes all tools and research packages)
pip install -e ".[dev,research]"

# Or if you prefer using requirements files
pip install -r requirements-dev.txt
```

**Note**: The `-e` flag installs in "editable" mode, which means changes to the code take effect immediately without reinstalling.

### 4. Verify Installation

```bash
# Verify core dependencies
python -c "import ib_insync; print(f'ib_insync version: {ib_insync.__version__}')"
python -c "import pandas; print(f'pandas version: {pandas.__version__}')"

# Verify the execution module is available
python -c "from execution import IBKROrderExecutor; print('✓ Execution module installed correctly')"

# Check dev tools
pytest --version
black --version
```

## IBKR TWS Configuration

### Paper Trading Setup (Recommended for Development)

1. **Download TWS or IB Gateway**
   - TWS: Full desktop application with GUI
   - IB Gateway: Lightweight, headless version (recommended for servers)
   - Download from: https://www.interactivebrokers.com/en/trading/tws.php

2. **Enable API Access**
   - Launch TWS/Gateway with your paper trading credentials
   - Go to: File → Global Configuration → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Add `127.0.0.1` to "Trusted IP Addresses"
   - Set Socket Port: `7497` (paper) or `7496` (live)
   - **Important**: Check "Read-Only API" for initial testing
   - Uncheck "Read-Only API" only when ready to submit real orders

3. **Configure Auto-Restart (Optional)**
   - API → Settings → "Auto restart" (recommended to avoid manual restarts)

### Environment Variables

Create a `.env` file in the project root (never commit this file):

```bash
# IBKR Connection
IBKR_HOST=127.0.0.1
IBKR_PORT=7497          # 7497=paper, 7496=live
IBKR_CLIENT_ID=1
IBKR_READONLY=false     # Set to true for read-only testing

# Timeout settings
IBKR_TIMEOUT_SECONDS=30
IBKR_RECONNECT_MAX_ATTEMPTS=5
IBKR_RECONNECT_BACKOFF_SECONDS=5

# Logging
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/execution.log
```

## Running Tests

```bash
# Run all tests
pytest

# Run unit tests only (no IBKR connection required)
pytest -m unit

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/execution/test_connection.py

# Run with verbose output
pytest -v

# Integration tests (requires TWS running)
pytest -m integration
```

## Code Quality Tools

```bash
# Format code with Black
black .

# Lint with Ruff
ruff check .

# Type check with mypy
mypy execution/ strategies/ backtesting/

# Run all checks before committing
black . && ruff check . && mypy . && pytest
```

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes following TDD**
   - Write tests first
   - Implement functionality
   - Run tests: `pytest`

3. **Format and lint**
   ```bash
   black .
   ruff check . --fix
   ```

4. **Type check**
   ```bash
   mypy execution/ strategies/
   ```

5. **Commit changes**
   ```bash
   git add .
   git commit -m "feat(execution): add order submission logic"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Troubleshooting

### Connection Issues

**Problem**: `ConnectionRefusedError` when connecting to TWS
- **Solution**: Ensure TWS/Gateway is running and API is enabled
- Check port number matches (7497 for paper, 7496 for live)
- Verify `127.0.0.1` is in Trusted IP Addresses

**Problem**: `error 326: Client ID already in use`
- **Solution**: Each connection needs a unique client ID
- Either disconnect existing connection or use different client ID
- Restart TWS/Gateway if issue persists

**Problem**: Orders rejected with "Read-Only API" error
- **Solution**: Uncheck "Read-Only API" in TWS API settings
- Restart TWS after changing setting

### Testing Issues

**Problem**: Integration tests fail
- **Solution**: Ensure TWS is running before running integration tests
- Use paper trading account for tests
- Check that test account has sufficient funds/margin

**Problem**: Type checking failures
- **Solution**: Some third-party libraries (ib_insync, pandas) may show type errors
- These are configured to be ignored in `pyproject.toml`
- Focus on type checking your own code

## Resources

- [IBKR API Documentation](https://interactivebrokers.github.io/tws-api/)
- [ib_insync Documentation](https://ib-insync.readthedocs.io/)
- [Project Design Document](execution/DESIGN.md)
- [Execution Module README](execution/README.md)

## Next Steps

Once setup is complete:
1. Run the test suite to verify everything works
2. Review the architecture in `execution/DESIGN.md`
3. Check out `execution/README.md` for module overview
4. Start with the examples (coming soon)

