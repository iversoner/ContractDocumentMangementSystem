"""
统一错误响应格式
"""
from flask import jsonify
import traceback
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """注册全局错误处理器"""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'success': False, 'message': str(e.description) if e.description else '请求参数错误'}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'success': False, 'message': '未登录或令牌已过期'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'success': False, 'message': '权限不足'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'success': False, 'message': '资源不存在'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'success': False, 'message': '请求方法不允许'}), 405

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"服务器内部错误: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': '服务器内部错误'}), 500

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        logger.error(f"未处理的异常: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'服务器错误: {str(e)}'}), 500
