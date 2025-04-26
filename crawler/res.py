# crawler/res.py

import requests,json,os

def get_ticket_data():
    # 数据
    config_path = os.path.join(os.path.dirname(__file__), "../config.json")
    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)
        url = config["url"]
        headers = config["headers"]
        data = config["data"]
    # 请求
    res = requests.post(url,json=data,headers=headers)
    data_dict = res.json()
    
    # 数据处理
    title = str(data_dict['data']['records'][0]['workorderDescription'])
    status = data_dict['data']['records'][0]['workorderStatusName']
    name = data_dict['data']['records'][0]['acceptName']
    feedback_time = data_dict['data']['records'][0]['feedBackTime']
    delimiter = "---------------------------------------------------------"
    # 格式化输出
    #print(f"{delimiter}\n\t{title}\n  状态：{status}\n  接单人：{name}\n  超时时间：{feedback_time}")
    return title, status, name, feedback_time