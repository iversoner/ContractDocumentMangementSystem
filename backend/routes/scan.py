"""
目录扫描 & 批量导入 API
扫描指定目录下的文件，识别哪些文件尚未录入系统，支持逐级浏览子目录、选择性批量导入
"""
import os
import re
from datetime import date

from flask import Blueprint, request, jsonify, g, current_app

from database.db import get_db
from services.log_service import write_log
from middleware.auth_middleware import login_required

scan_bp = Blueprint('scan', __name__)

# 支持的文件扩展名
FILE_EXTS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.txt', '.zip', '.rar'}

# 按模块已有的 file_path 查询
TABLE_MAP = {
    'contract': 'contracts',
    'patent': 'patents',
    'insurance': 'insurances',
}


def _translate_path(windows_path: str, host_data_dir: str):
    """将 Windows 路径翻译为容器内 Linux 路径。

    如果 windows_path 以 host_data_dir 开头（不区分大小写），
    则将前缀替换为 /data。否则返回 None 表示路径不在允许范围内。
    """
    if not host_data_dir:
        return None

    # 规范化路径
    norm_input = os.path.normpath(windows_path.strip())
    norm_host = os.path.normpath(host_data_dir.strip())

    # 去掉末尾的路径分隔符，避免 startswith 匹配问题
    norm_input = norm_input.rstrip('\\')
    norm_host = norm_host.rstrip('\\')

    # 不区分大小写比较（Windows 路径）
    if norm_input.lower() == norm_host.lower():
        return '/data'

    if norm_input.lower().startswith(norm_host.lower() + '\\'):
        # 截取剩余路径
        remaining = norm_input[len(norm_host):]
        if remaining.startswith('\\'):
            remaining = remaining[1:]
        # 反斜杠转为正斜杠
        linux_remaining = remaining.replace('\\', '/')
        return '/data/' + linux_remaining

    return None


def _scan_dir_nonrecursive(root_dir: str, ext_filter: set = None) -> dict:
    """扫描指定目录（非递归），返回当前目录的文件和子目录列表。

    Returns:
        {
            'files': [{name, path, size}, ...],
            'subdirs': ['dirname1', 'dirname2', ...],
            'currentDir': str,
            'parentDir': str or None
        }
    """
    if ext_filter is None:
        ext_filter = FILE_EXTS

    files = []
    subdirs = []

    if not os.path.isdir(root_dir):
        return {'files': [], 'subdirs': [], 'currentDir': os.path.normpath(root_dir), 'parentDir': None}

    try:
        entries = sorted(os.listdir(root_dir))
    except PermissionError:
        entries = []

    for entry in entries:
        full_path = os.path.join(root_dir, entry)
        if os.path.isfile(full_path):
            ext = os.path.splitext(entry)[1].lower()
            if ext in ext_filter:
                files.append({
                    'name': entry,
                    'path': os.path.normpath(full_path),
                    'size': os.path.getsize(full_path),
                })
        elif os.path.isdir(full_path):
            subdirs.append(entry)

    # 计算父目录
    parent = os.path.normpath(os.path.join(root_dir, '..'))
    if os.path.normpath(parent) == os.path.normpath(root_dir):
        parent = None

    return {
        'files': files,
        'subdirs': subdirs,
        'currentDir': os.path.normpath(root_dir),
        'parentDir': parent,
    }


@scan_bp.route('/api/scan', methods=['POST'])
@login_required
def scan_directory():
    """扫描指定目录（非递归），返回当前目录文件列表、子目录列表及是否已在系统中"""
    data = request.get_json() or {}
    directory = data.get('directory', '').strip()
    module = data.get('module', 'contract').strip()

    if not directory:
        return jsonify({'success': False, 'message': '请提供扫描目录路径'}), 400
    if module not in TABLE_MAP:
        return jsonify({'success': False, 'message': '模块类型无效'}), 400

    # ---- 路径翻译 ----
    host_data_dir = current_app.config.get('HOST_DATA_DIR', '')

    if '\\' in directory or ':' in directory:
        # 看起来像 Windows 路径，尝试翻译
        translated = _translate_path(directory, host_data_dir)
        if translated is None:
            return jsonify({
                'success': False,
                'message': f'仅支持{host_data_dir}下的目录！',
                'errorType': 'invalid_path'
            }), 400
        scan_dir = translated
    else:
        # 已经是 Linux 容器路径，直接使用
        scan_dir = directory

    if not os.path.isdir(scan_dir):
        return jsonify({
            'success': False,
            'message': f'目录不存在: {directory}',
            'errorType': 'dir_not_found'
        }), 400

    # ---- 非递归扫描 ----
    result = _scan_dir_nonrecursive(scan_dir)

    # 查询已录入的文件路径
    table = TABLE_MAP[module]
    db = get_db()
    existing_rows = db.execute(
        f"SELECT file_path FROM {table} WHERE file_path != ''"
    ).fetchall()
    existing_paths = set()
    for r in existing_rows:
        existing_paths.add(os.path.normpath(r['file_path']))

    # 区分已录入和未录入
    new_files = []
    existing_files = []
    for f in result['files']:
        if f['path'] in existing_paths:
            existing_files.append(f)
        else:
            new_files.append(f)

    return jsonify({
        'success': True,
        'data': {
            'directory': directory,
            'translatedDir': scan_dir,
            'module': module,
            'currentDir': result['currentDir'],
            'parentDir': result['parentDir'],
            'subdirs': result['subdirs'],
            'total': len(result['files']),
            'newCount': len(new_files),
            'existingCount': len(existing_files),
            'newFiles': new_files,
            'existingFiles': existing_files,
        }
    })


@scan_bp.route('/api/scan/import', methods=['POST'])
@login_required
def bulk_import():
    """批量导入扫描到的文件"""
    data = request.get_json() or {}
    module = data.get('module', 'contract').strip()
    files = data.get('files', [])  # [{path: ..., name: ...}]
    category = data.get('category', '')

    if module not in TABLE_MAP:
        return jsonify({'success': False, 'message': '模块类型无效'}), 400
    if not files:
        return jsonify({'success': False, 'message': '请提供要导入的文件列表'}), 400

    table = TABLE_MAP[module]
    db = get_db()
    today = date.today().isoformat()
    imported = 0
    skipped = 0

    for f in files:
        file_path = f.get('path', '')
        file_name = f.get('name', '')
        if not file_path:
            skipped += 1
            continue

        # 检查是否已存在
        existing = db.execute(
            f"SELECT id FROM {table} WHERE file_path = ?", (file_path,)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        # 从文件名提取名称（去掉扩展名）
        name_no_ext = os.path.splitext(file_name)[0]

        if module == 'contract':
            db.execute(
                f"INSERT INTO {table} (name, category, company, agent, start_date, end_date, file_path, source, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'scan', 'active')",
                (name_no_ext, category or '未分类', '', '', today, today, file_path)
            )
        elif module == 'patent':
            db.execute(
                f"INSERT INTO {table} (name, patent_no, type, holder, agent, application_date, expire_date, file_path, source, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'scan', 'active')",
                (name_no_ext, 'AUTO-' + name_no_ext[:20], '', '', '', today, today, file_path)
            )
        elif module == 'insurance':
            db.execute(
                f"INSERT INTO {table} (plate_no, brand, insurance_company, insurance_type, agent, start_date, end_date, file_path, source, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'scan', 'active')",
                (name_no_ext, name_no_ext, '', '', '', today, today, file_path)
            )
        imported += 1

    db.commit()
    write_log(action='批量导入', module=f'{module}管理',
              detail=f'扫描导入 {imported} 条记录（跳过 {skipped} 条已存在）',
              user_id=g.user_id, username=g.username)

    return jsonify({
        'success': True,
        'message': f'成功导入 {imported} 条记录（跳过 {skipped} 条已存在）',
        'data': {'imported': imported, 'skipped': skipped}
    })
