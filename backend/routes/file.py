"""
文件管理 API
"""
import os
import uuid

from flask import Blueprint, request, jsonify, g, send_file, current_app
from werkzeug.utils import secure_filename

from database.db import get_db
from database.db import utc_to_beijing
from services.log_service import write_log
from middleware.auth_middleware import login_required, admin_required

file_bp = Blueprint('file', __name__)

ALLOWED_CATEGORIES = ['合同', '专利', '车险续期']


def _get_upload_dir():
    rel_path = current_app.config.get('STORAGE_UPLOAD_FOLDER', 'backend/uploads')
    if not os.path.isabs(rel_path):
        rel_path = os.path.join(current_app.root_path, '..', rel_path)
    abs_path = os.path.normpath(rel_path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def _row_to_dict(r) -> dict:
    return {
        'id': r['id'],
        'name': r['name'],
        'category': r['category'],
        'size': r['size'],
        'uploader': r['uploader'] or '',
        'storedPath': r['stored_path'],
        'createdAt': str(r['created_at']),
    }


@file_bp.route('', methods=['GET'])
@login_required
def list_files():
    db = get_db()
    category = request.args.get('category', '').strip()
    keyword = request.args.get('keyword', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    page_size = max(1, min(100, request.args.get('pageSize', 10, type=int)))

    where = []
    params = []
    if category:
        where.append("category = ?")
        params.append(category)
    if keyword:
        where.append("name LIKE ?")
        params.append(f'%{keyword}%')

    where_sql = (' AND '.join(where)) if where else '1=1'

    total = db.execute(f"SELECT COUNT(*) FROM files WHERE {where_sql}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM files WHERE {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, (page - 1) * page_size]
    ).fetchall()

    return jsonify({
        'success': True,
        'data': {
            'items': [_row_to_dict(r) for r in rows],
            'total': total,
            'page': page,
            'pageSize': page_size,
        }
    })


@file_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    f = request.files['file']
    if f.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400

    category = request.form.get('category', '合同')
    if category not in ALLOWED_CATEGORIES:
        return jsonify({'success': False, 'message': f'文件类别必须是: {", ".join(ALLOWED_CATEGORIES)}'}), 400

    # 文件大小检查
    max_size = current_app.config.get('STORAGE_MAX_FILE_SIZE', 10 * 1024 * 1024)
    f.seek(0, os.SEEK_END)
    file_size = f.tell()
    f.seek(0)
    if file_size > max_size:
        return jsonify({'success': False, 'message': f'文件大小超过限制 ({max_size // 1024 // 1024} MB)'}), 400

    # 保存文件
    original_name = secure_filename(f.filename)
    ext = os.path.splitext(original_name)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = _get_upload_dir()
    stored_path = os.path.join(upload_dir, stored_name)
    f.save(stored_path)

    db = get_db()
    cursor = db.execute(
        "INSERT INTO files (name, category, size, uploader, stored_path) VALUES (?, ?, ?, ?, ?)",
        (original_name, category, file_size, g.username, stored_path)
    )
    db.commit()
    new_id = cursor.lastrowid

    write_log(action='上传文件', module='文件管理', detail=f'上传文件「{original_name}」(ID={new_id})',
              user_id=g.user_id, username=g.username)

    r = db.execute("SELECT * FROM files WHERE id = ?", (new_id,)).fetchone()
    return jsonify({'success': True, 'message': '文件上传成功', 'data': _row_to_dict(r)}), 201


@file_bp.route('/<int:id>/download', methods=['GET'])
def download_file(id):
    # 支持 URL 参数 token（用于 a 标签直接下载）
    token = request.args.get('token', '')
    if token:
        from services.auth_service import verify_token
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'message': '令牌无效或已过期'}), 401
    else:
        # 否则使用 header Bearer token
        from middleware.auth_middleware import login_required as _check
        pass  # 让后续代码手动检查

    if not token:
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': '未提供认证令牌'}), 401
        t = auth_header[7:]
        from services.auth_service import verify_token
        payload = verify_token(t)
        if not payload:
            return jsonify({'success': False, 'message': '令牌无效或已过期'}), 401

    db = get_db()
    r = db.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
    if not r:
        return jsonify({'success': False, 'message': '文件不存在'}), 404

    stored_path = r['stored_path']
    if not os.path.exists(stored_path):
        return jsonify({'success': False, 'message': '文件已被删除或移动'}), 404

    write_log(action='下载文件', module='文件管理', detail=f'下载文件「{r["name"]}」(ID={id})',
              user_id=payload.get('user_id'), username=payload.get('username', ''))

    return send_file(stored_path, as_attachment=True, download_name=r['name'])


@file_bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def delete_file(id):
    db = get_db()
    r = db.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
    if not r:
        return jsonify({'success': False, 'message': '文件不存在'}), 404

    # 删除物理文件
    stored_path = r['stored_path']
    try:
        if os.path.exists(stored_path):
            os.remove(stored_path)
    except OSError:
        pass

    db.execute("DELETE FROM files WHERE id = ?", (id,))
    db.commit()
    write_log(action='删除文件', module='文件管理', detail=f'删除文件「{r["name"]}」(ID={id})',
              user_id=g.user_id, username=g.username)

    return jsonify({'success': True, 'message': '文件已删除'})
