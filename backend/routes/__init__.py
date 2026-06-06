"""
蓝图注册
"""


def register_blueprints(app):
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.contract import contract_bp
    from routes.patent import patent_bp
    from routes.insurance import insurance_bp
    from routes.file import file_bp
    from routes.user import user_bp
    from routes.log import log_bp
    from routes.setting import setting_bp
    from routes.export import export_bp
    from routes.scan import scan_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(contract_bp, url_prefix='/api/contracts')
    app.register_blueprint(patent_bp, url_prefix='/api/patents')
    app.register_blueprint(insurance_bp, url_prefix='/api/insurances')
    app.register_blueprint(file_bp, url_prefix='/api/files')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(log_bp, url_prefix='/api/logs')
    app.register_blueprint(setting_bp, url_prefix='/api/settings')
    app.register_blueprint(export_bp, url_prefix='/api/export')
    app.register_blueprint(scan_bp, url_prefix='/api/scan')
