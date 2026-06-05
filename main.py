#main.py

import json, requests
import uuid
from datetime import datetime, timezone
from flask import Flask, render_template, send_from_directory, abort, request, redirect, url_for, flash, jsonify
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
import os
from crawler.res import get_ticket_data

app = Flask(__name__)
DOWNLOAD_DIRECTORY = "download"  # 定义下载目录
SETTING_FILE = "setting.json"  # 设置文件路径

CACHE_DIR = "cache"
ADMIN_COOKIE_FILE = os.path.join(CACHE_DIR, "admin_cookies.json")

# 默认设置
DEFAULT_SETTINGS = {
    "water_token": ""
}

# 初始化应用（创建必要的目录和配置文件）
def init_app():
    os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(SETTING_FILE):
        save_settings(DEFAULT_SETTINGS)
    # 检测 secret_key.txt，不存在则创建，默认写入 kyrian
    if not os.path.exists('secret_key.txt'):
        with open('secret_key.txt', 'w', encoding='utf-8') as f:
            f.write('kyrian')

# 读取设置文件
def load_settings():
    try:
        if os.path.exists(SETTING_FILE):
            with open(SETTING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

# 保存设置文件
def save_settings(settings):
    try:
        with open(SETTING_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
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
                modified_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
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
    try:
        with open('secret_key.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

#上传文件
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            flash('未选择文件')
            return redirect(url_for('list_directory'))
        
        file = request.files['file']
        if file.filename == '':
            flash('未选择文件')
            return redirect(url_for('list_directory'))
        
        # 验证密钥
        secret_key = get_secret_key()
        if not secret_key:
            flash('服务器配置错误')
            return redirect(url_for('list_directory'))
            
        provided_key = request.form.get('secret_key', '')
        if provided_key != secret_key:
            flash('无效的上传密钥')
            return redirect(url_for('list_directory'))
        
        # 确保文件名安全
        filename = secure_filename(file.filename)
        if not filename:
            flash('无效的文件名')
            return redirect(url_for('list_directory'))
        
        # 保存文件到download目录
        filepath = os.path.join(DOWNLOAD_DIRECTORY, filename)
        file.save(filepath)
        flash('文件上传成功')
        return redirect(url_for('list_directory'))
        
    except Exception as e:
        app.logger.error(f'上传错误: {str(e)}')
        flash('文件上传失败')
        return redirect(url_for('index'))

#关于页面
@app.route('/about')
def about():
    return render_template('about.html', current_page='about')

#工单数据API
@app.route('/get_ticket_data')
def get_ticket_info():
    try:
        ticket_data = get_ticket_data()
        return jsonify(ticket_data)
    except Exception as e:
        app.logger.error(f'获取工单数据错误: {str(e)}')
        return jsonify({
            'title': '获取失败',
            'status': '错误',
            'assignee': '未知',
            'timeout': '未知'
        }), 500

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
    versions = get_wbtools_versions()
    sort = request.args.get('sort', 'versionCode,desc')
    if sort == 'versionCode,asc':
        versions.sort(key=lambda x: x['versionCode'])
    else:
        versions.sort(key=lambda x: x['versionCode'], reverse=True)
    return jsonify(versions)


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


#启动
if __name__ == "__main__":
    init_app()  # 初始化应用
    app.secret_key = 'your-secret-key-here'  # 用于flash消息
    app.run(host="0.0.0.0", port=5000, debug=True)
