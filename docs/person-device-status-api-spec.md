# 万物云人员设备状态 API 开发文档

## 接口地址

`POST https://heimdallr.onewo.com/api/headquarter/zyt/last/allDevice`

## 请求参数

```json
{
  "name": "",
  "projectCode": "52010017",
  "type": "1",
  "limitFlag": 1
}
```

| 参数 | 说明 | 默认值 | 是否暴露 |
|---|---|---|---|
| name | 人员姓名，为空则查询项目全体 | 空 | ✅ 可改 |
| projectCode | 项目编码 | 52010017 | ✅ 可改 |
| type | 设备类型 | 1 | ❌ 封装 |
| limitFlag | 限制标识 | 1 | ❌ 封装 |

## 返回格式

```json
{
  "isOk": true,
  "msg": "",
  "cause": "",
  "code": "200",
  "data": [
    {
      "longitude": 106.73834333372082,
      "latitude": 26.559704926273113,
      "status": "1",
      "name": "李仕科",
      "mobile": "13639137932",
      "roleName": "项目安防主管",
      "sipCode": "8811061116047",
      "type": "1",
      "num": 0
    }
  ]
}
```

### 关键字段

| 字段 | 说明 |
|---|---|
| status | 1=在线 |
| longitude / latitude | 经度 / 纬度 |
| name | 人员姓名 |
| mobile | 手机号 |
| roleName | 角色名称 |
| sipCode | SIP 编号 |

### 离线情况

人员不在线时，请求正常返回 200，**data 为空数组**：

```json
{
  "isOk": true,
  "msg": "",
  "cause": "",
  "code": "200",
  "data": []
}
```

## 鉴权

请求头中已包含长期有效的 token，**可直接长期使用**，无需频繁更新。

## 注意事项

- `name` 为空 → 查询该项目全体人员
- `projectCode` 可按需修改指定项目
- 若人员未开启手机定位，返回的 `longitude` 与 `latitude` 均为 `0.0`
