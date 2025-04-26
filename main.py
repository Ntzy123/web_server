#main.py

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

#启动
if __name__ == "__main__":
    app.secret_key = 'your-secret-key-here'  # 用于flash消息
    app.run(host="0.0.0.0", port=5000, debug=True)