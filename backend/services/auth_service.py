"""
认证服务：密码哈希、JWT 生成与验证
"""
import datetime
import bcrypt
import jwt

from flask import current_app


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password: str, password_hash: str) -> bool:
    """验证密码是否正确"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def generate_token(user_id: int, username: str, role: str) -> str:
    """生成 JWT token（24小时有效）"""
    secret_key = current_app.config.get('SECRET_KEY', 'suzhen-secret')
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def verify_token(token: str) -> dict:
    """验证 JWT token，返回 payload；失败返回 None"""
    secret_key = current_app.config.get('SECRET_KEY', 'suzhen-secret')
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
