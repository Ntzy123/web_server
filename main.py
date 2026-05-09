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
#遍历目录
def list_files(directory):
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

#设置download路由
@app.route('/download')
def list_directory():
    files = list_files(DOWNLOAD_DIRECTORY)
    return render_template('download.html', files=files)

#下载文件
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_DIRECTORY, filename, as_attachment=True)



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