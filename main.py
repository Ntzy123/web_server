#main.py

import requests
from datetime import datetime
from flask import Flask, render_template, send_from_directory, abort, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
from crawler.res import get_ticket_data

app = Flask(__name__)
DOWNLOAD_DIRECTORY = "download"  # 定义下载目录

# 确保下载目录存在
os.makedirs(DOWNLOAD_DIRECTORY, exist_ok=True)


#主页
@app.route('/')
def index():
    return render_template('index.html')


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
    
    # 确保是目录
    if not os.path.isdir(full_path):
        abort(404)
    
    items = list_directory_contents(full_path, safe_path)
    return render_template('download.html', items=items, current_path=safe_path)

#下载文件
@app.route('/download/<path:filepath>')
def download_file(filepath):
    # 安全处理路径
    safe_path = os.path.normpath(filepath)
    if safe_path.startswith('..') or safe_path.startswith('/') or safe_path.startswith('\\'):
        abort(403)
    
    full_path = os.path.join(DOWNLOAD_DIRECTORY, safe_path)
    
    # 确保路径在下载目录内
    if not os.path.abspath(full_path).startswith(os.path.abspath(DOWNLOAD_DIRECTORY)):
        abort(403)
    
    # 确保是文件
    if not os.path.isfile(full_path):
        abort(404)
    
    return send_from_directory(DOWNLOAD_DIRECTORY, safe_path, as_attachment=True)



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
    return render_template('about.html')

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


# 桶装水数据API
@app.route('/api/water')
def get_water_data():
    """获取桶装水订单数据并统计"""
    try:
        # 获取查询日期，默认当天
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

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
            "x-token-auth": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJBQ0NFU1NfVE9LRU4iLCJjbGllbnRJZCI6ImJmOTcxOTZiN2YwZDRiODI4MzI2MTIyZDAyYjZhNTFiIiwic2NvcGUiOiJyLXN0YWZmIiwidG9rZW4iOiIxNzAyMDcxIiwiaWF0IjoxNzc3Nzk4ODg1LCJleHAiOjE3Nzg0MDM2ODV9.P3P8nKzFz7aoF0epzHmehbfpKgd7056EfUZSY2d1T4E",
            "x-requested-with": "com.vanke.wyguide",
            "referer": "https://neighbor.4009515151.com/andariel/water?at=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJBQ0NFU1NfVE9LRU4iLCJjbGllbnRJZCI6ImJmOTcxOTZiN2YwZDRiODI4MzI2MTIyZDAyYjZhNTFiIiwic2NvcGUiOiJyLXN0YWZmIiwidG9rZW4iOiIxNzAyMDcxIiwiaWF0IjoxNzc3Nzk4ODg1LCJleHAiOjE3Nzg0MDM2ODV9.P3P8nKzFz7aoF0epzHmehbfpKgd7056EfUZSY2d1T4E",
            "Cookie": "tgw_l7_route=27ac1799876fd00610bcbaf4410a86af; access_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJBQ0NFU1NfVE9LRU4iLCJjbGllbnRJZCI6ImJmOTcxOTZiN2YwZDRiODI4MzI2MTIyZDAyYjZhNTFiIiwic2NvcGUiOiJyLXN0YWZmIiwidG9rZW4iOiIxNzAyMDcxIiwiaWF0IjoxNzc3Nzk4ODg1LCJleHAiOjE3Nzg0MDM2ODV9.P3P8nKzFz7aoF0epzHmehbfpKgd7056EfUZSY2d1T4E"
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


#启动
if __name__ == "__main__":
    app.secret_key = 'your-secret-key-here'  # 用于flash消息
    app.run(host="0.0.0.0", port=5000, debug=True)