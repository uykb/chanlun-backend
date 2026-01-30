from flask import send_from_directory
from flask_cors import CORS
from web.chanlun_chart.cl_app import create_app
import os

app = create_app()
# 允许跨域请求，优先从环境变量读取
cors_origins = os.getenv('CORS_ORIGINS', '*')
CORS(app, resources={r"/*": {"origins": cors_origins.split(',') if ',' in cors_origins else cors_origins}})

# 静态前端页面服务
@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join('frontend', path)):
        return send_from_directory('frontend', path)
    return "Not Found", 404

# 添加一个初始化配置接口，供静态前端使用
@app.route('/api/init_config')
def init_config():
    from chanlun.base import Market
    from chanlun.exchange import get_exchange
    from tzlocal import get_localzone
    
    market_frequencys = {
        "a": list(get_exchange(Market.A).support_frequencys().keys()),
        "hk": list(get_exchange(Market.HK).support_frequencys().keys()),
        "fx": list(get_exchange(Market.FX).support_frequencys().keys()),
        "us": list(get_exchange(Market.US).support_frequencys().keys()),
        "futures": list(get_exchange(Market.FUTURES).support_frequencys().keys()),
        "ny_futures": list(get_exchange(Market.NY_FUTURES).support_frequencys().keys()),
        "currency": list(get_exchange(Market.CURRENCY).support_frequencys().keys()),
        "currency_spot": list(get_exchange(Market.CURRENCY_SPOT).support_frequencys().keys()),
    }
    
    market_default_codes = {
        "a": get_exchange(Market.A).default_code(),
        "hk": get_exchange(Market.HK).default_code(),
        "fx": get_exchange(Market.FX).default_code(),
        "us": get_exchange(Market.US).default_code(),
        "futures": get_exchange(Market.FUTURES).default_code(),
        "ny_futures": get_exchange(Market.NY_FUTURES).default_code(),
        "currency": get_exchange(Market.CURRENCY).default_code(),
        "currency_spot": get_exchange(Market.CURRENCY_SPOT).default_code(),
    }

    return {
        "market_frequencys": market_frequencys,
        "market_default_codes": market_default_codes,
        "server_timezone": str(get_localzone())
    }

if __name__ == '__main__':
    host = os.getenv('WEB_HOST', '0.0.0.0')
    port = int(os.getenv('WEB_PORT', 5000))
    app.run(host=host, port=port)
