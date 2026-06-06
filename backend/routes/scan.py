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


@scan_bp.route('', methods=['POST'])
@login_required
def scan_directory():
    """扫描指定目录（非递归），返回当前目录文件列表、子目录列表及是否已在系统中"""
    data = request.get_json() or {}
    directory = data.get('directory', '').strip()
    module = data.get('module', 'contract').strip()

    if module not in TABLE_MAP:
        return jsonify({'success': False, 'message': '模块类型无效'}), 400

    # 默认扫描 /data 目录
    if not directory:
        directory = '/data'

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

    # 查询已录入的文件路径和文件名
    table = TABLE_MAP[module]
    db = get_db()
    existing_rows = db.execute(
        f"SELECT file_path, file_name FROM {table} WHERE file_path != '' OR file_name != ''"
    ).fetchall()
    existing_paths = set()
    existing_names = set()
    for r in existing_rows:
        if r['file_path']:
            existing_paths.add(os.path.normpath(r['file_path']))
        if r['file_name']:
            existing_names.add(r['file_name'])

    # 区分已录入和未录入（file_path 或 file_name 任一匹配即视为已存在）
    def _is_existing(f):
        return f['path'] in existing_paths or f['name'] in existing_names

    new_files = []
    existing_files = []
    for f in result['files']:
        if _is_existing(f):
            existing_files.append(f)
        else:
            new_files.append(f)

    # 对每个子目录，计算其中的新文件数（浅层扫描一层）
    subdirs_with_count = []
    for sd in result['subdirs']:
        sd_path = os.path.join(result['currentDir'], sd)
        sd_result = _scan_dir_nonrecursive(sd_path)
        sd_new = 0
        sd_total = len(sd_result['files'])
        for f in sd_result['files']:
            if not _is_existing(f):
                sd_new += 1
        subdirs_with_count.append({
            'name': sd,
            'path': os.path.normpath(sd_path),
            'newCount': sd_new,
            'totalCount': sd_total,
            'hasSubdirs': len(sd_result['subdirs']) > 0,
        })

    return jsonify({
        'success': True,
        'data': {
            'directory': directory,
            'translatedDir': scan_dir,
            'module': module,
            'currentDir': result['currentDir'],
            'parentDir': result['parentDir'],
            'subdirs': subdirs_with_count,
            'total': len(result['files']),
            'newCount': len(new_files),
            'existingCount': len(existing_files),
            'newFiles': new_files,
            'existingFiles': existing_files,
        }
    })


@scan_bp.route('/import', methods=['POST'])
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

        # 检查是否已存在（按 file_path 或 file_name 匹配）
        existing = db.execute(
            f"SELECT id FROM {table} WHERE file_path = ? OR (file_name != '' AND file_name = ?)",
            (file_path, file_name)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        # 从文件名提取名称（去掉扩展名）
        name_no_ext = os.path.splitext(file_name)[0]

        if module == 'contract':
            db.execute(
                f"INSERT INTO {table} (name, category, company, agent, start_date, end_date, file_path, file_name, source, status, is_complete) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'scan', 'active', 0)",
                (name_no_ext, category or '未分类', '', '', today, today, file_path, file_name)
            )
        elif module == 'patent':
            db.execute(
                f"INSERT INTO {table} (name, patent_no, type, holder, agent, application_date, expire_date, file_path, file_name, source, status, is_complete) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scan', 'active', 0)",
                (name_no_ext, 'AUTO-' + name_no_ext[:20], '', '', '', today, today, file_path, file_name)
            )
        elif module == 'insurance':
            db.execute(
                f"INSERT INTO {table} (plate_no, brand, insurance_company, insurance_type, agent, start_date, end_date, file_path, file_name, source, status, is_complete) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scan', 'active', 0)",
                (name_no_ext, name_no_ext, '', '', '', today, today, file_path, file_name)
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


@scan_bp.route('/import-dirs', methods=['POST'])
@login_required
def import_directories():
    """导入指定目录列表下的所有新文件（递归扫描每个目录）"""
    data = request.get_json() or {}
    module = data.get('module', 'contract').strip()
    dirs = data.get('dirs', [])  # list of directory paths
    category = data.get('category', '')

    if module not in TABLE_MAP:
        return jsonify({'success': False, 'message': '模块类型无效'}), 400
    if not dirs:
        return jsonify({'success': False, 'message': '请选择要导入的目录'}), 400

    table = TABLE_MAP[module]
    db = get_db()
    today = date.today().isoformat()

    # 查询已存在的 file_path 和 file_name
    existing_rows = db.execute(
        f"SELECT file_path, file_name FROM {table} WHERE file_path != '' OR file_name != ''"
    ).fetchall()
    existing_paths = set()
    existing_names = set()
    for r in existing_rows:
        if r['file_path']:
            existing_paths.add(os.path.normpath(r['file_path']))
        if r['file_name']:
            existing_names.add(r['file_name'])

    imported = 0
    skipped = 0

    def _recursive_collect(directory):
        """递归收集目录下所有支持的文件"""
        collected = []
        if not os.path.isdir(directory):
            return collected
        try:
            entries = sorted(os.listdir(directory))
        except PermissionError:
            return collected
        for entry in entries:
            full = os.path.join(directory, entry)
            if os.path.isfile(full):
                ext = os.path.splitext(entry)[1].lower()
                if ext in FILE_EXTS:
                    collected.append({
                        'name': entry,
                        'path': os.path.normpath(full),
                    })
            elif os.path.isdir(full):
                collected.extend(_recursive_collect(full))
        return collected

    for d in dirs:
        files = _recursive_collect(d)
        for f in files:
            file_path = f['path']
            file_name = f['name']
            if file_path in existing_paths or file_name in existing_names:
                skipped += 1
                continue
            name_no_ext = os.path.splitext(file_name)[0]

            if module == 'contract':
                db.execute(
                    f"INSERT INTO {table} (name, category, company, agent, start_date, end_date, file_path, file_name, source, status, is_complete) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'scan', 'active', 0)",
                    (name_no_ext, category or '未分类', '', '', today, today, file_path, file_name)
                )
            elif module == 'patent':
                db.execute(
                    f"INSERT INTO {table} (name, patent_no, type, holder, agent, application_date, expire_date, file_path, file_name, source, status, is_complete) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scan', 'active', 0)",
                    (name_no_ext, 'AUTO-' + name_no_ext[:20], '', '', '', today, today, file_path, file_name)
                )
            elif module == 'insurance':
                db.execute(
                    f"INSERT INTO {table} (plate_no, brand, insurance_company, insurance_type, agent, start_date, end_date, file_path, file_name, source, status, is_complete) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scan', 'active', 0)",
                    (name_no_ext, name_no_ext, '', '', '', today, today, file_path, file_name)
                )
            existing_paths.add(file_path)
            existing_names.add(file_name)
            imported += 1

    db.commit()
    write_log(action='批量导入', module=f'{module}管理',
              detail=f'扫描导入 {imported} 条记录（跳过 {skipped} 条已存在），涉及 {len(dirs)} 个目录',
              user_id=g.user_id, username=g.username)

    return jsonify({
        'success': True,
        'message': f'成功导入 {imported} 条记录（跳过 {skipped} 条已存在）',
        'data': {'imported': imported, 'skipped': skipped}
    })
