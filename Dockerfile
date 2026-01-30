FROM python:3.11-slim as builder

# 安装编译依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 编译安装 TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib*

# 最终镜像
FROM python:3.11-slim

# 复制 TA-Lib 库文件
COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/include/ta-lib/ /usr/include/ta-lib/

WORKDIR /app

# 安装运行依赖
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
# 额外安装 flask-cors 用于前后端分离
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir flask-cors gunicorn gevent TA-Lib tzlocal

# 复制源代码
COPY src/ /app/src/
COPY web/ /app/web/
COPY package/ /app/package/
RUN cp src/chanlun/config.py.demo src/chanlun/config.py
COPY frontend/ /app/frontend/
COPY app_cors.py /app/app_cors.py

# 安装本地 pytdx
RUN pip install /app/package/pytdx-1.72r2-py3-none-any.whl

# 设置环境变量
ENV PYTHONPATH=/app/src
ENV FLASK_APP=app_cors.py

# 暴露端口
EXPOSE 5000

# 启动命令（使用 gevent 提升并发并降低资源占用）
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--worker-class", "gevent", "app_cors:app"]
