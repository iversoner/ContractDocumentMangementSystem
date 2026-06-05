"""
素珍管理系统 - Flask 应用工厂
"""
import os
import logging

from yaml import safe_load as yaml_load
from flask import Flask
from flask_cors import CORS


def create_app(config_path=None):
    """创建并配置 Flask 应用"""
    app = Flask(__name__)

    # ---- 加载配置 ----
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml_load(f)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', config['app']['secret_key'])
    app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', str(config['app'].get('debug', False))).lower() == 'true'
    app.config['SERVER_HOST'] = os.environ.get('SERVER_HOST', config['server']['host'])
    app.config['SERVER_PORT'] = int(os.environ.get('SERVER_PORT', config['server']['port']))
    app.config['DATABASE_PATH'] = os.environ.get('DATABASE_PATH', config['database']['path'])
    app.config['ADMIN_CONFIG'] = config['admin']
    app.config['STORAGE_UPLOAD_FOLDER'] = os.environ.get('STORAGE_UPLOAD_FOLDER', config['storage']['upload_folder'])
    app.config['STORAGE_MAX_FILE_SIZE'] = int(os.environ.get('STORAGE_MAX_FILE_SIZE', config['storage']['max_file_size']))
    app.config['EMAIL_SMTP_SERVER'] = os.environ.get('EMAIL_SMTP_SERVER', config['email']['smtp_server'])
    app.config['EMAIL_SMTP_PORT'] = int(os.environ.get('EMAIL_SMTP_PORT', config['email']['smtp_port']))
    app.config['EMAIL_USERNAME'] = os.environ.get('EMAIL_USERNAME', config['email']['username'])
    app.config['EMAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD', config['email']['password'])
    app.config['EMAIL_USE_TLS'] = os.environ.get('EMAIL_USE_TLS', str(config['email']['use_tls'])).lower() == 'true'
    app.config['EMAIL_SENDER_NAME'] = os.environ.get('EMAIL_SENDER_NAME', config['email']['sender_name'])
    app.config['REMINDER_ENABLED'] = os.environ.get('REMINDER_ENABLED', str(config['reminder']['enabled'])).lower() == 'true'
    app.config['REMINDER_DAYS_BEFORE'] = int(os.environ.get('REMINDER_DAYS_BEFORE', config['reminder']['days_before']))
    app.config['HOST_DATA_DIR'] = os.environ.get('HOST_DATA_DIR', config.get('host_data_dir', ''))

    # ---- CORS 跨域 ----
    CORS(app, supports_credentials=True)

    # ---- 日志配置 ----
    logging.basicConfig(
        level=logging.DEBUG if app.config['DEBUG'] else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # ---- 初始化数据库 ----
    from database.db import init_app as init_db
    init_db(app)

    # ---- 注册蓝图 ----
    from routes import register_blueprints
    register_blueprints(app)

    # ---- 注册错误处理 ----
    from middleware.error_handler import register_error_handlers
    register_error_handlers(app)

    app.logger.info(f"{config['app']['name']} 启动完成")
    return app
