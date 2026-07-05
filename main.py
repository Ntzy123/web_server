#main.py

import json, requests
import uuid, zoneinfo
import threading, time
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, send_from_directory, abort, request, redirect, url_for, flash, jsonify
from urllib.parse import urlparse
from math import radians, cos, sin, asin, sqrt
from config.core.api_defs import HEIMDALLR_HEADERS, API_DEFS
from config.core.toml_util import load as toml_load, dump as toml_dump
# 安全处理文件名：防路径穿越，保留中文和特殊字符
def safe_filename(filename):
    # 移除路径分隔符，防止路径穿越
    filename = filename.replace('/', '_').replace('\\', '_')
    # 移除控制字符（除空格外的所有 c < ' ' 字符，含 \t \r \n \0）
    filename = ''.join(c for c in filename if c >= ' ')
    # 移除首尾空白
    filename = filename.strip(' .')
    # 压缩连续空格（保留连续下划线，如 __UNI__ 是合法命名）
    import re
    filename = re.sub(r'  +', ' ', filename)
    return filename if filename else 'untitled'
import os
from crawler.res import get_night_check_data

app = Flask(__name__)
DOWNLOAD_DIRECTORY = "download"  # 定义下载目录
CONFIG_RUNTIME_DIR = "config_runtime"
SETTING_FILE = os.path.join(CONFIG_RUNTIME_DIR, "settings.toml")
PERSON_DEVICE_STATUS_CONFIG = os.path.join(CONFIG_RUNTIME_DIR, "person_device_status.toml")

CACHE_DIR = "cache"
ADMIN_COOKIE_FILE = os.path.join(CACHE_DIR, "admin_cookies.json")

# 最大上传 2GB
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
# 增大表单内存缓冲（16MB 以内直接内存，超过写临时文件）
app.config['MAX_FORM_MEMORY_SIZE'] = 16 * 1024 * 1024

# 全局 500 错误处理器，输出异常到控制台
@app.errorhandler(500)
def internal_error(e):
    import traceback
    traceback.print_exc()
    return "Internal Server Error", 500

# 413 返回 JSON（而非默认 HTML）
@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({'error': '文件大小超过限制（最大 2GB）'}), 413

# 默认设置（在 settings.toml 创建时使用）
_DEFAULT_SETTINGS = {
    "water_token": ""
}

# 初始化应用（创建必要的目录和配置文件）
def init_app():
    os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(CONFIG_RUNTIME_DIR, exist_ok=True)

    # 设置文件 settings.toml
    if not os.path.exists(SETTING_FILE):
        save_settings(_DEFAULT_SETTINGS)

    # secret_key.txt（保持 txt 格式，不涉及结构变化）
    secret_key_path = os.path.join(CONFIG_RUNTIME_DIR, 'secret_key.txt')
    if not os.path.exists(secret_key_path):
        with open(secret_key_path, 'w', encoding='utf-8') as f:
            f.write('kyrian')

    # person_device_status 运行时配置文件
    if not os.path.exists(PERSON_DEVICE_STATUS_CONFIG):
        _init_pd_config()

# 读取设置文件（TOML）
def load_settings():
    data = toml_load(SETTING_FILE)
    return data if data is not None else {}


# 保存设置文件（TOML）
def save_settings(settings):
    try:
        toml_dump(settings, SETTING_FILE)
        return True
    except Exception as e:
        app.logger.error(f'保存设置错误: {str(e)}')
        return False

# 获取water_token（纯token）
def get_water_token():
    settings = load_settings()
    return settings.get('water_token', '')

# ========== Admin Cookie Management ==========

def load_admin_cookies():
    try:
        if os.path.exists(ADMIN_COOKIE_FILE):
            with open(ADMIN_COOKIE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception:
        return []


def save_admin_cookies(cookies):
    try:
        with open(ADMIN_COOKIE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        app.logger.error(f'保存管理员Cookie错误: {str(e)}')
        return False

# ========== WBTools Version Management ==========

def _generate_version_id(versions):
    if not versions:
        return 1
    return max(v['id'] for v in versions) + 1


def get_wbtools_versions():
    settings = load_settings()
    return settings.get('wbtools_versions', [])


def save_wbtools_versions(versions):
    settings = load_settings()
    settings['wbtools_versions'] = versions
    return save_settings(settings)


def _is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except:
        return False


def validate_version_data(data, is_update=False):
    errors = []
    if not is_update or 'versionCode' in data:
        vc = data.get('versionCode')
        if vc is None or not isinstance(vc, int) or vc < 1:
            errors.append('versionCode 必须为正整数')
    if not is_update or 'versionName' in data:
        vn = data.get('versionName')
        if not vn or not isinstance(vn, str) or not vn.strip():
            errors.append('versionName 不能为空')
    if not is_update or 'downloadUrl' in data:
        url = data.get('downloadUrl', '')
        if url and not _is_valid_url(url):
            errors.append('downloadUrl 格式不正确')
    return errors


# ===================================================================


#主页
@app.route('/')
def index():
    return render_template('index.html', current_page='index')


###/download下载页面
#格式化文件大小
def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

#遍历目录，返回文件和文件夹信息
def list_directory_contents(directory, base_path=""):
    items = []
    
    # 获取当前目录中的所有条目
    try:
        entries = os.listdir(directory)
    except (PermissionError, OSError):
        return []
    
    for entry in entries:
        full_path = os.path.join(directory, entry)
        relative_path = os.path.join(base_path, entry) if base_path else entry
        
        if os.path.isdir(full_path):
            # 文件夹
            items.append({
                'name': entry,
                'path': relative_path,
                'is_dir': True,
                'size': '-',
                'modified': '-'
            })
        elif os.path.isfile(full_path):
            # 文件
            try:
                stat = os.stat(full_path)
                # 将文件时间戳转换为北京时间 (UTC+8)
                utc_dt = datetime.fromtimestamp(stat.st_mtime, tz=zoneinfo.ZoneInfo("UTC"))
                shanghai_dt = utc_dt.astimezone(zoneinfo.ZoneInfo("Asia/Shanghai"))
                modified_time = shanghai_dt.strftime('%Y-%m-%d %H:%M:%S')
                size = stat.st_size
            except (PermissionError, OSError):
                modified_time = '未知'
                size = 0
            
            items.append({
                'name': entry,
                'path': relative_path,
                'is_dir': False,
                'size': format_size(size),
                'size_bytes': size,
                'modified': modified_time
            })
    
    # 排序：文件夹在前，然后按名称排序
    items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    return items

#设置download路由
@app.route('/download')
@app.route('/download/<path:subpath>')
def list_directory(subpath=""):
    # 安全处理路径，防止目录遍历攻击
    safe_path = os.path.normpath(subpath)
    if safe_path.startswith('..') or safe_path.startswith('/') or (safe_path and safe_path.startswith('\\')):
        abort(403)
    
    full_path = os.path.join(DOWNLOAD_DIRECTORY, safe_path) if safe_path else DOWNLOAD_DIRECTORY
    
    # 确保路径在下载目录内
    if not os.path.abspath(full_path).startswith(os.path.abspath(DOWNLOAD_DIRECTORY)):
        abort(403)
    
    # 如果是文件，直接下载
    if os.path.isfile(full_path):
        return send_from_directory(DOWNLOAD_DIRECTORY, safe_path, as_attachment=True)
    
    # 如果是目录，显示文件列表
    if os.path.isdir(full_path):
        items = list_directory_contents(full_path, safe_path)
        return render_template('download.html', items=items, current_path=safe_path, current_page='download')
    
    abort(404)



# 读取密钥文件
def get_secret_key():
    secret_key_path = os.path.join(CONFIG_RUNTIME_DIR, 'secret_key.txt')
    try:
        with open(secret_key_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

# 检测文件是否已存在（用于前端确认覆盖）
@app.route('/api/check_duplicate')
def check_duplicate():
    filename = request.args.get('filename', '')
    subpath = request.args.get('subpath', '')
    if not filename:
        return jsonify({'exists': False})
    safe_name = safe_filename(filename)
    target_dir = os.path.join(DOWNLOAD_DIRECTORY, subpath) if subpath else DOWNLOAD_DIRECTORY
    # 防止路径穿越
    if not os.path.abspath(target_dir).startswith(os.path.abspath(DOWNLOAD_DIRECTORY)):
        return jsonify({'exists': False})
    filepath = os.path.join(target_dir, safe_name)
    return jsonify({'exists': os.path.exists(filepath), 'filename': safe_name})


#上传文件
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # 验证管理员cookie
        token = request.cookies.get('admin_token', '')
        if not token:
            app.logger.warning('上传请求未携带 admin_token cookie (可能来自移动端)')
            return jsonify({'error': '未授权'}), 403
        cookies = load_admin_cookies()
        if not any(c['token'] == token for c in cookies):
            return jsonify({'error': '管理员身份已过期'}), 403

        if 'file' not in request.files:
            return jsonify({'error': '未选择文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400

        # 确保文件名安全
        filename = safe_filename(file.filename)
        if not filename:
            return jsonify({'error': '无效的文件名'}), 400

        # 支持上传到子目录
        subpath = request.form.get('subpath', '')
        if subpath:
            # 安全处理子路径
            safe_sub = os.path.normpath(subpath)
            if safe_sub.startswith('..') or safe_sub.startswith('/') or safe_sub.startswith('\\'):
                return jsonify({'error': '无效的路径'}), 400
            target_dir = os.path.join(DOWNLOAD_DIRECTORY, safe_sub)
            if not os.path.abspath(target_dir).startswith(os.path.abspath(DOWNLOAD_DIRECTORY)):
                return jsonify({'error': '无效的路径'}), 400
            os.makedirs(target_dir, exist_ok=True)
        else:
            target_dir = DOWNLOAD_DIRECTORY

        filepath = os.path.join(target_dir, filename)

        # 文件覆盖保护：未传 overwrite 参数且文件已存在则拒绝
        overwrite = request.form.get('overwrite', '0') == '1'
        if os.path.exists(filepath) and not overwrite:
            return jsonify({'exists': True, 'filename': filename}), 409

        file.save(filepath)
        return jsonify({'success': True, 'message': '上传成功'})

    except Exception as e:
        app.logger.error(f'上传错误: {str(e)}')
        return jsonify({'error': '上传失败: ' + str(e)}), 500

#关于页面
@app.route('/about')
def about():
    return render_template('about.html', current_page='about')

#工单数据API（暂时禁用）
@app.route('/get_ticket_data')
def get_ticket_info():
    # 该接口暂时禁用
    # try:
    #     ticket_data = get_night_check_data()
    #     return jsonify(ticket_data)
    # except Exception as e:
    #     app.logger.error(f'获取工单数据错误: {str(e)}')
    #     return jsonify({
    #         'title': '获取失败',
    #         'status': '错误',
    #         'assignee': '未知',
    #         'timeout': '未知'
    #     }), 500
    return jsonify({'error': '该接口已暂时禁用'}), 503

# ticket_timeout 授权
@app.route('/api/get_auth')
def get_auth():
    return "OK"


# 配置页面
@app.route('/settings')
def settings_page():
    current_settings = load_settings()
    return render_template('settings.html', settings=current_settings, current_page='settings')


# 获取所有设置API
@app.route('/api/settings')
def get_settings():
    return jsonify(load_settings())


# 保存设置API
@app.route('/api/settings', methods=['POST'])
def update_settings():
    try:
        data = request.get_json()
        current_settings = load_settings()
        current_settings.update(data)
        if save_settings(current_settings):
            return jsonify({'success': True, 'message': '保存成功'})
        return jsonify({'success': False, 'message': '保存失败'}), 500
    except Exception as e:
        app.logger.error(f'更新设置错误: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


# 桶装水数据API
@app.route('/api/water')
def get_water_data():
    """获取桶装水订单数据并统计"""
    try:
        # 获取查询日期，默认当天
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        water_token = get_water_token()
        
        if not water_token:
            return jsonify({
                'success': False,
                'message': '未配置water_token'
            }), 400

        url = (
            f"https://neighbor.4009515151.com/mephisto/merchant/itemorder/waitconfrim"
            f"?searchStartTime={date_str}"
            f"&searchEndTime={date_str}"
            f"&pageNum=1"
            f"&pageSize=100"
            f"&goodsType=2"
        )

        headers = {
            "User-Agent": "VKStaffAssistant-Android-6.44.0-Mozilla/5.0 (Linux; Android 16; 2210132C Build/BP2A.250605.031.A3; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.164 Mobile Safari/537.36",
            "x-token-phone": "18085009482",
            "x-token-auth": water_token,
            "x-requested-with": "com.vanke.wyguide",
            "referer": f"https://neighbor.4009515151.com/andariel/water?at={water_token}",
            "Cookie": f"tgw_l7_route=27ac1799876fd00610bcbaf4410a86af; access_token={water_token}"
        }

        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()

        if data.get('code') != 0 or not data.get('success'):
            return jsonify({
                'success': False,
                'message': '获取数据失败',
                'raw_data': data
            }), 500

        order_list = data.get('data', {}).get('list', [])

        # 过滤8:30-20:30下单的订单
        filtered_orders = []
        for order in order_list:
            take_time = order.get('takeTime', '')
            if not take_time:
                continue
            try:
                dt = datetime.strptime(take_time, '%Y-%m-%d %H:%M:%S')
                time_minutes = dt.hour * 60 + dt.minute
                start_minutes = 8 * 60 + 30
                end_minutes = 20 * 60 + 30
                if start_minutes <= time_minutes <= end_minutes:
                    filtered_orders.append(order)
            except (ValueError, TypeError):
                continue

        # 统计送水人员
        waiters = {}
        for order in filtered_orders:
            waiter_name = order.get('waiterName', '未知')
            waiter_mobile = order.get('waiterMobile', '')
            appointment_num = order.get('appointmentNum', 1)
            if waiter_name not in waiters:
                waiters[waiter_name] = {
                    'name': waiter_name,
                    'mobile': waiter_mobile,
                    'order_count': 0,
                    'total_buckets': 0
                }
            waiters[waiter_name]['order_count'] += 1
            waiters[waiter_name]['total_buckets'] += appointment_num

        return jsonify({
            'success': True,
            'query_date': date_str,
            'total_buckets': sum(o.get('appointmentNum', 1) for o in filtered_orders),
            'deliverers': list(waiters.values())
        })

    except Exception as e:
        app.logger.error(f'获取桶装水数据错误: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }), 500


# ========== WBTools Version API ==========


@app.route('/api/wbtools_version', methods=['GET'])
def list_wbtools_versions():
    try:
        versions = get_wbtools_versions()
        sort = request.args.get('sort', 'versionCode,desc')
        if sort == 'versionCode,asc':
            versions.sort(key=lambda x: x['versionCode'])
        else:
            versions.sort(key=lambda x: x['versionCode'], reverse=True)
        return jsonify(versions)
    except Exception as e:
        app.logger.error(f'获取版本列表错误: {str(e)}')
        return jsonify({'error': '获取版本列表失败'}), 500


@app.route('/api/wbtools_version/latest', methods=['GET'])
def get_latest_wbtools_version():
    versions = get_wbtools_versions()
    if not versions:
        return jsonify({'error': '暂无版本记录'}), 404
    latest = max(versions, key=lambda x: x['versionCode'])
    return jsonify(latest)


@app.route('/api/wbtools_version', methods=['POST'])
def create_wbtools_version():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    errors = validate_version_data(data)
    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    versions = get_wbtools_versions()

    vc = data['versionCode']
    if any(v['versionCode'] == vc for v in versions):
        return jsonify({'error': f'versionCode {vc} 已存在'}), 409

    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    new_version = {
        'id': _generate_version_id(versions),
        'versionCode': vc,
        'versionName': data['versionName'],
        'forceUpdate': data.get('forceUpdate', False),
        'updateDesc': data.get('updateDesc', ''),
        'downloadUrl': data.get('downloadUrl', ''),
        'createdAt': now,
        'updatedAt': now
    }

    versions.append(new_version)
    save_wbtools_versions(versions)

    return jsonify(new_version), 201


@app.route('/api/wbtools_version/<int:version_id>', methods=['PUT'])
def update_wbtools_version(version_id):
    versions = get_wbtools_versions()
    version = next((v for v in versions if v['id'] == version_id), None)
    if not version:
        return jsonify({'error': '版本不存在'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    if 'versionCode' in data:
        vc = data['versionCode']
        if vc != version['versionCode']:
            if any(v['versionCode'] == vc for v in versions):
                return jsonify({'error': f'versionCode {vc} 已存在'}), 409

    errors = validate_version_data(data, is_update=True)
    if errors:
        return jsonify({'error': '; '.join(errors)}), 400

    for key in ['versionCode', 'versionName', 'forceUpdate', 'updateDesc', 'downloadUrl']:
        if key in data:
            version[key] = data[key]

    version['updatedAt'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    save_wbtools_versions(versions)

    return jsonify(version), 200


@app.route('/api/wbtools_version/<int:version_id>', methods=['DELETE'])
def delete_wbtools_version(version_id):
    versions = get_wbtools_versions()
    version = next((v for v in versions if v['id'] == version_id), None)
    if not version:
        return jsonify({'error': '版本不存在'}), 404

    versions = [v for v in versions if v['id'] != version_id]
    save_wbtools_versions(versions)

    return '', 204


# ===================================================================
# ========== Admin Auth API ==========

@app.route('/api/admin/auth', methods=['POST'])
def admin_auth():
    """验证管理员密钥，生成并返回cookie token"""
    data = request.get_json()
    provided_key = data.get('key', '')
    secret_key = get_secret_key()
    if not secret_key:
        return jsonify({'success': False, 'message': '服务器未配置密钥'}), 500
    if provided_key != secret_key:
        return jsonify({'success': False, 'message': '密钥错误'}), 403

    # 生成唯一token
    token = str(uuid.uuid4())
    cookies = load_admin_cookies()
    now_str = datetime.now(timezone.utc).isoformat()
    cookies.append({'token': token, 'created_at': now_str})

    # 超过10个时移除最早的一条
    if len(cookies) > 10:
        cookies.sort(key=lambda c: c.get('created_at', ''))
        cookies = cookies[-10:]

    save_admin_cookies(cookies)

    response = jsonify({'success': True, 'token': token})
    response.set_cookie('admin_token', token, max_age=7 * 24 * 3600)
    return response


@app.route('/api/admin/check')
def admin_check():
    """检查当前请求的管理员cookie是否有效"""
    token = request.cookies.get('admin_token', '')
    if not token:
        return jsonify({'is_admin': False})
    cookies = load_admin_cookies()
    is_valid = any(c['token'] == token for c in cookies)
    return jsonify({'is_admin': is_valid})


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """移除当前cookie，退出管理员模式"""
    token = request.cookies.get('admin_token', '')
    cookies = load_admin_cookies()
    cookies = [c for c in cookies if c['token'] != token]
    save_admin_cookies(cookies)
    return jsonify({'success': True})

# ===================================================================
# ========== Person Device Status (人员设备状态) ==========

PERSON_DEVICE_STATUS_CACHE = os.path.join(CACHE_DIR, "person_device_status.json")
PERSON_DEVICE_STATUS_HISTORY_CACHE = os.path.join(CACHE_DIR, "person_device_status_history.json")

_PD_API = API_DEFS["person_device_status"]
PERSON_DEVICE_STATUS_URL = _PD_API["url"]
MAX_HISTORY_RECORDS = 100


def _init_pd_config():
    """初始化 person_device_status 运行时 TOML 配置（使用 api_defs 中的默认值）"""
    default = {
        "name": _PD_API["default_payload"]["name"],
        "project_code": _PD_API["default_payload"]["projectCode"],
        "project_center_lon": 106.73841555681847,
        "project_center_lat": 26.559202447498212,
    }
    toml_dump(default, PERSON_DEVICE_STATUS_CONFIG)


def _load_pd_config():
    """读取运行时配置，缺失字段回退到默认值"""
    cfg = toml_load(PERSON_DEVICE_STATUS_CONFIG) or {}
    return {
        "name": cfg.get("name", _PD_API["default_payload"]["name"]),
        "project_code": cfg.get("project_code", _PD_API["default_payload"]["projectCode"]),
        "center_lon": cfg.get("project_center_lon", 106.73841555681847),
        "center_lat": cfg.get("project_center_lat", 26.559202447498212),
    }


def haversine_distance(lon1, lat1, lon2, lat2):
    """计算两点间距离（米），使用 Haversine 公式"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return c * 6371000  # 地球平均半径（米）


def query_person_device_status():
    """查询指定人员的设备位置状态，结果写入缓存"""
    pd_cfg = _load_pd_config()
    person_name = pd_cfg["name"]
    project_code = pd_cfg["project_code"]
    center_lon = pd_cfg["center_lon"]
    center_lat = pd_cfg["center_lat"]

    timestamp = int(time.time() * 1000)
    payload = {
        "name": person_name,
        "projectCode": project_code,
        "type": "1",
        "limitFlag": 1,
    }

    try:
        resp = requests.post(PERSON_DEVICE_STATUS_URL, json=payload, headers=HEIMDALLR_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        app.logger.error(f"人员设备状态查询失败: {e}")
        _write_location_cache(timestamp, False, "500", [
            {"name": person_name, "distance_m": 0, "status": "0"}
        ])
        return

    is_ok = data.get("isOk", False)
    code = data.get("code", "500")
    raw_list = data.get("data", [])

    found = None
    for item in raw_list:
        if item.get("name") == person_name:
            found = item
            break

    if found and found.get("status") == "1":
        lon = found.get("longitude", 0)
        lat = found.get("latitude", 0)
        if lon and lat:
            distance = round(haversine_distance(center_lon, center_lat, lon, lat), 2)
            record = {"name": person_name, "distance_m": distance, "status": "1"}
        else:
            # 设备在线但未开启定位，lat/lon 为 0
            record = {"name": person_name, "distance_m": 0, "status": "1"}
    else:
        # 设备离线
        record = {"name": person_name, "distance_m": 0, "status": "0"}

    _write_location_cache(timestamp, is_ok, code, [record])


def _append_location_history(timestamp, record):
    """向历史记录追加一条，保留最近 MAX_HISTORY_RECORDS 条"""
    history = []
    if os.path.exists(PERSON_DEVICE_STATUS_HISTORY_CACHE):
        try:
            with open(PERSON_DEVICE_STATUS_HISTORY_CACHE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            pass

    entry = {
        "timestamp": timestamp,
        "name": record.get("name", ""),
        "status": record.get("status", "0"),
        "distance_m": record.get("distance_m", 0),
    }
    history.append(entry)

    if len(history) > MAX_HISTORY_RECORDS:
        history = history[-MAX_HISTORY_RECORDS:]

    tmp = PERSON_DEVICE_STATUS_HISTORY_CACHE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PERSON_DEVICE_STATUS_HISTORY_CACHE)


def _write_location_cache(timestamp, is_ok, code, records):
    """将结果写入最新缓存，并根据变化追加历史记录"""
    # 先读取当前最新缓存，获取前一条用于比较
    prev_status = None
    prev_distance = None
    if os.path.exists(PERSON_DEVICE_STATUS_CACHE):
        try:
            with open(PERSON_DEVICE_STATUS_CACHE, 'r', encoding='utf-8') as f:
                prev_data = json.load(f)
            prev_records = prev_data.get("records", [])
            if prev_records:
                prev_status = prev_records[0].get("status")
                prev_distance = prev_records[0].get("distance_m", 0)
        except Exception:
            pass

    # 写入最新缓存（临时文件 + 原子重命名）
    data = {
        "timestamp": timestamp,
        "is_ok": is_ok,
        "code": code,
        "records": records,
    }
    tmp = PERSON_DEVICE_STATUS_CACHE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PERSON_DEVICE_STATUS_CACHE)

    # 判断是否需要追加历史记录
    if records:
        cur = records[0]
        cur_status = cur.get("status")
        cur_distance = cur.get("distance_m", 0)

        should_record = False
        if prev_status is None:
            should_record = True  # 首次记录
        elif cur_status != prev_status:
            should_record = True  # 状态发生变化
        elif abs(cur_distance - prev_distance) > 100:
            should_record = True  # 距离变化超过 100 米

        if should_record:
            _append_location_history(timestamp, cur)


def _scheduler_loop():
    """定时循环：每分钟 0 秒时查询一次（不重试）"""
    while True:
        now = datetime.now()
        next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        sleep_seconds = (next_minute - now).total_seconds()
        time.sleep(sleep_seconds)
        query_person_device_status()


@app.route('/api/person-device-status/location-latest')
def person_device_location_latest():
    """返回最新缓存的位置数据"""
    if not os.path.exists(PERSON_DEVICE_STATUS_CACHE):
        return jsonify({"error": "暂无数据"}), 404
    try:
        with open(PERSON_DEVICE_STATUS_CACHE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/person-device-status/location-history')
def person_device_location_history():
    """返回位置历史记录列表"""
    if not os.path.exists(PERSON_DEVICE_STATUS_HISTORY_CACHE):
        return jsonify([])
    try:
        with open(PERSON_DEVICE_STATUS_HISTORY_CACHE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===================================================================


#启动
if __name__ == "__main__":
    init_app()  # 初始化应用
    app.secret_key = 'your-secret-key-here'  # 用于flash消息

    # 启动人员设备状态定时查询（守护线程，每分钟 0 秒执行）
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()

    print("服务器已启动: http://0.0.0.0:5000")
    from waitress import serve
    serve(app,
          host="0.0.0.0",
          port=5000,
          threads=8,
          max_request_body_size=2147483648,  # 2GB，与 MAX_CONTENT_LENGTH 一致
          recv_bytes=65536)  # 增大接收缓冲，大文件上传更快

