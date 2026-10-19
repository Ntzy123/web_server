# config/core/api_defs.py
"""万科/万物云 API 定义层：认证头 + 各接口 URL / 方法 / 默认请求体"""

# ============================================================
# 共享认证头（所有 heimdallr 接口共用）
# ============================================================
HEIMDALLR_HEADERS = {
    "Authorization": "sys:web:tokeneyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiLmnY7ku5Xnp5EiLCJ1c2VySWQiOiJjMTY3Y2Y5NDcwNGY0YjdhYWE4YjUzZGNmMmQ3Zjk4NSIsIm5pa2VOYW1lIjoi5p2O5LuV56eRIiwiY29tcGFueUlkIjoiMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAiLCJleHAiOjE3NDU3MTg5NDB9.j9I3R-kctxcB3CQzMSsBcUXa8OVes9ux5UedJzaWE8WWwOxKKCwRVWgHKubcu2aD-rdQFFQfZuRYMAieu3WAV-b8GrwIstAqydscpr9d20mEcGkQzc8-IWF0LeUFMOCOF7CWJzFNtFqZrCbDzijpYzV791vx-xT-r1r14tymd5s",
    "Content-Type": "application/json",
    "type": "heimdallr",
    "systemId": "0e9e407230db4436a56ca1d0df23c255",
    "USER": "c167cf94704f4b7aaa8b53dcf2d7f985",
    "COMPANY": "00000000000000000000000000000000",
    "System-Tag": "web",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# ============================================================
# API 定义
# ============================================================
API_DEFS = {

    # --------------------------------------------------
    # 1. 夜查工单查询（暂时禁用）
    # --------------------------------------------------
    "night_check": {
        "url": "https://heimdallr.onewo.com/api/task/courier/admin/task/work-order/queryCourierTaskWorkOrderEtlPage",
        "method": "POST",
        "description": "查询夜查工单详细信息",
        "default_payload": {
            "workorderNo": "Na000008837805220250421_2_4",
            "createMobile": "",
            "projectId": "",
            "workorderStatus": (
                '["1","1001","1002","1003","1004","1005","1013",'
                '"1014","4040","6","3","4","5","1006","1007",'
                '"1008","1015","4041","10","1017","1091"]'
            ),
            "sourceKeyList": [],
            "date1": [],
            "workOrderTypeNoListOld": [],
            "current": 1,
            "limit": 10,
            "startTime": "",
            "endTime": "",
            "type": "1",
        },
    },

    # --------------------------------------------------
    # 2. 人员设备位置查询
    #    默认参数（运行时被 config_runtime/person_device_status.toml 覆盖）
    # --------------------------------------------------
    "person_device_status": {
        "url": "https://heimdallr.onewo.com/api/headquarter/zyt/last/allDevice",
        "method": "POST",
        "description": "查询指定人员在项目范围内的最新设备位置",
        "default_payload": {
            "name": "李仕科",
            "projectCode": "52010017",
            "type": "1",
            "limitFlag": 1,
        },
        "default_project_code": "52010017",
    },
}
