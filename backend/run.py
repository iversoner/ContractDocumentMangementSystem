"""
素珍管理系统 - 后端启动入口
支持：python run.py（开发） / gunicorn run:app（生产）
"""
import os
import sys

# 确保 backend 目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    host = app.config.get('SERVER_HOST', '0.0.0.0')
    port = app.config.get('SERVER_PORT', 5000)
    debug = app.config.get('DEBUG', True)

    print(f"""
======================================
  素珍管理系统 - 后端服务
======================================
  地址: http://{host}:{port}
  调试: {'开启' if debug else '关闭'}
  API:  http://{host}:{port}/api
======================================
""")

    app.run(host=host, port=port, debug=debug)
