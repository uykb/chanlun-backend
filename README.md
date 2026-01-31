# Chanlun Backend

Chanlun Backend is the API service for the Chanlun Market Analysis Tool, providing缠论 (Chan Lun) market analysis, data feeds, and historical data retrieval.

## Features

- **缠论 Analysis**: Real-time market data analysis based on 缠论 theory.
- **Multi-Market Support**: Supports A-shares, HK stocks, US stocks, Forex, Futures, and Cryptocurrencies.
- **API Service**: Provides RESTful APIs for the frontend application.
- **Static Serving**: Can serve the frontend static files directly.

## Prerequisites

- Python 3.11+
- TA-Lib (Technical Analysis Library)
- Dependencies listed in `requirements.txt`

## Installation

### Option 1: Using Docker (Recommended)

1. Build the Docker image:
   ```bash
   docker build -t chanlun-backend .
   ```

2. Run the container:
   ```bash
   docker run -d \
     -p 5000:5000 \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/config_dir:/app/config \
     --name chanlun-backend \
     chanlun-backend
   ```

   - **Port**: The application runs on port 5000 by default.
   - **Data Volume**: Mount a volume to `/app/data` to persist your market data.
   - **Configuration (Directory Mount)**: If your platform only supports mounting directories (disks), mount a directory to `/app/config` and place your `config.py` file inside that directory. The application will automatically load it.
   - **License Key**: If you have a PyArmor license file (`license.lic` or `.pyarmor.ikey`), place it in the same `/app/config` directory. The application will automatically detect and apply it at startup.

### Option 2: Local Installation

1. **Install System Dependencies**:
   You need to install TA-Lib. On Ubuntu/Debian:
   ```bash
   wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
   tar -xzf ta-lib-0.4.0-src.tar.gz
   cd ta-lib/
   ./configure --prefix=/usr
   make
   sudo make install
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install flask-cors gunicorn gevent TA-Lib tzlocal
   ```

3. **Configure the Application**:
   Copy the example configuration and edit it:
   ```bash
   cp src/chanlun/config.py.demo src/chanlun/config.py
   # Edit src/chanlun/config.py with your settings
   ```

4. **Run the Service**:
   ```bash
   # Using Gunicorn (Recommended for production)
   gunicorn --bind 0.0.0.0:5000 --workers 2 --worker-class gevent app_cors:app

   # Or using Flask development server (Debug only)
   python app_cors.py
   ```

## Configuration

The application is configured via `src/chanlun/config.py`. Key settings include:

- `WEB_HOST`: Host address (e.g., `0.0.0.0`).
- `LOGIN_PASSWORD`: Password for web access (optional).
- `DATA_PATH`: Directory for storing local data.
- `EXCHANGE_*`: Configuration for different market data sources (e.g., `EXCHANGE_A = "tdx"`).

Refer to the full config file for all available options.

## API Endpoints

- `GET /`: Serves the frontend application (if served by backend).
- `GET /api/init_config`: Returns initialization configuration for the frontend.
- Other缠论 analysis endpoints are defined in `web/chanlun_chart/cl_app.py`.

## Environment Variables

The following environment variables can override default settings:

- `WEB_HOST`: Server host (default: `0.0.0.0`).
- `WEB_PORT`: Server port (default: `5000`).
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated). **Important**: If you deploy the frontend on Vercel, add your Vercel domain here (e.g., `https://your-app.vercel.app`).

## Project Structure

```
/backend
├── app_cors.py           # Main Flask application entry point
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker build configuration
├── src/
│   ├── chanlun/         # Core缠论 logic
│   ├── cl_myquant/      # MyQuant integration
│   ├── cl_vnpy/         # VN.py integration
│   └── cl_wtpy/         # WTPy integration
├── frontend/            # Frontend static files
├── web/                 # Web interface logic
└── package/             # Local packages (e.g., pytdx)
```
