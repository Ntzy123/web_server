# crawler/res.py
"""夜查工单查询"""

import requests
from config.core.api_defs import HEIMDALLR_HEADERS, API_DEFS


def get_night_check_data():
    """查询夜查工单详情"""
    api = API_DEFS["night_check"]
    payload = api["default_payload"].copy()

    resp = requests.post(api["url"], json=payload, headers=HEIMDALLR_HEADERS)
    data_dict = resp.json()

    record = data_dict["data"]["records"][0]
    return {
        "title": str(record["workorderDescription"]),
        "status": record["workorderStatusName"],
        "assignee": record["acceptName"],
        "timeout": record["feedBackTime"],
    }
