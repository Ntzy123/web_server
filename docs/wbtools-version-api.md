# WBTools Version API
 
> 版本管理接口，提供 WBTools 应用版本的增删改查与升级检查能力。
> Base URL: `http://<host>:5000`
 
---
 
## 目录
 
- [数据模型](#数据模型)
- [1. 获取版本列表](#1-获取版本列表)
- [2. 获取最新版本](#2-获取最新版本)
- [3. 新增版本](#3-新增版本)
- [4. 编辑版本](#4-编辑版本)
- [5. 删除版本](#5-删除版本)
- [附录：错误码说明](#附录错误码说明)
 
---
 
## 数据模型
 
### Version 对象
 
| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `id` | `Long` | 自动生成 | 唯一标识，用于编辑与删除 |
| `versionCode` | `Integer` | **是** | 版本号，全局唯一，用于排序与比较；必须为正整数 |
| `versionName` | `String` | **是** | 展示给用户的版本名称，不能为空 |
| `forceUpdate` | `Boolean` | 否 | 强制更新标记，仅对最新版本有意义；默认 `false` |
| `updateDesc` | `String` | 否 | 更新日志全文；前端控制溢出截断 |
| `downloadUrl` | `String` | 否 | APK 下载直链或落地页 URL，若提供必须为合法 HTTP(S) 地址 |
| `createdAt` | `String` | 自动生成 | 创建时间，ISO 8601 格式（`2026-06-01T10:00:00Z`） |
| `updatedAt` | `String` | 自动生成 | 最后更新时间，ISO 8601 格式 |
 
---
 
## 1. 获取版本列表
 
> 返回所有版本，默认按 `versionCode` 降序排列（新版本在前）。
 
### 请求
 
```
GET /api/wbtools_version
```
 
### 查询参数
 
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `sort` | `String` | 否 | `versionCode,desc` | 排序方式。`versionCode,desc` 降序，`versionCode,asc` 升序 |
 
### 请求示例
 
```bash
curl http://localhost:5000/api/wbtools_version
```
 
```bash
# 指定升序排列
curl "http://localhost:5000/api/wbtools_version?sort=versionCode,asc"
```
 
### 成功响应
 
```
HTTP/1.1 200 OK
Content-Type: application/json
```
 
```json
[
  {
    "id": 3,
    "versionCode": 13,
    "versionName": "v2.4.0",
    "forceUpdate": false,
    "updateDesc": "新增功能B，优化界面性能",
    "downloadUrl": "https://example.com/app-v2.4.0.apk",
    "createdAt": "2026-06-04T08:00:00Z",
    "updatedAt": "2026-06-04T08:00:00Z"
  },
  {
    "id": 2,
    "versionCode": 12,
    "versionName": "v2.3.1",
    "forceUpdate": true,
    "updateDesc": "修复若干问题，优化性能",
    "downloadUrl": "https://example.com/app-v2.3.1.apk",
    "createdAt": "2026-06-01T10:00:00Z",
    "updatedAt": "2026-06-03T12:00:00Z"
  }
]
```
 
### 空列表响应
 
```json
[]
```
 
---
 
## 2. 获取最新版本
 
> 按 `versionCode` 取最大值，用于客户端升级检查。
 
### 请求
 
```
GET /api/wbtools_version/latest
```
 
### 请求示例
 
```bash
curl http://localhost:5000/api/wbtools_version/latest
```
 
### 成功响应
 
```
HTTP/1.1 200 OK
Content-Type: application/json
```
 
```json
{
  "id": 3,
  "versionCode": 13,
  "versionName": "v2.4.0",
  "forceUpdate": false,
  "updateDesc": "新增功能B，优化界面性能",
  "downloadUrl": "https://example.com/app-v2.4.0.apk",
  "createdAt": "2026-06-04T08:00:00Z",
  "updatedAt": "2026-06-04T08:00:00Z"
}
```
 
### 失败响应
 
```
HTTP/1.1 404 NOT FOUND
Content-Type: application/json
```
 
```json
{
  "error": "暂无版本记录"
}
```
 
---
 
## 3. 新增版本
 
> 创建一个新版本。`versionCode` 必须全局唯一。
 
### 请求
 
```
POST /api/wbtools_version
Content-Type: application/json
```
 
### 请求体参数
 
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `versionCode` | `Integer` | **是** | — | 版本号，必须为正整数，且不与已有版本重复 |
| `versionName` | `String` | **是** | — | 版本名称，不能为空 |
| `forceUpdate` | `Boolean` | 否 | `false` | 是否强制更新 |
| `updateDesc` | `String` | 否 | `""` | 更新日志 |
| `downloadUrl` | `String` | 否 | `""` | 下载地址，若提供须为合法 HTTP(S) URL |
 
### 请求示例
 
```bash
curl -X POST http://localhost:5000/api/wbtools_version \
  -H "Content-Type: application/json" \
  -d '{
    "versionCode": 13,
    "versionName": "v2.4.0",
    "forceUpdate": false,
    "updateDesc": "新增功能B，优化界面性能",
    "downloadUrl": "https://example.com/app-v2.4.0.apk"
  }'
```
 
### 成功响应
 
```
HTTP/1.1 201 CREATED
Content-Type: application/json
```
 
```json
{
  "id": 3,
  "versionCode": 13,
  "versionName": "v2.4.0",
  "forceUpdate": false,
  "updateDesc": "新增功能B，优化界面性能",
  "downloadUrl": "https://example.com/app-v2.4.0.apk",
  "createdAt": "2026-06-04T08:00:00Z",
  "updatedAt": "2026-06-04T08:00:00Z"
}
```
 
### 失败响应
 
**参数校验错误（400）**
 
```
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json
```
 
```json
{
  "error": "versionCode 必须为正整数; versionName 不能为空; downloadUrl 格式不正确"
}
```
 
**版本号冲突（409）**
 
```
HTTP/1.1 409 CONFLICT
Content-Type: application/json
```
 
```json
{
  "error": "versionCode 13 已存在"
}
```
 
---
 
## 4. 编辑版本
 
> 更新指定版本的字段。采用部分更新（Partial Update），未提供的字段保持原值。
 
### 请求
 
```
PUT /api/wbtools_version/{id}
Content-Type: application/json
```
 
### 路径参数
 
| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | `Long` | 版本唯一标识，从列表接口获取 |
 
### 请求体参数
 
与创建接口一致，但所有字段均为可选（至少提供一个字段）。
 
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `versionCode` | `Integer` | 否 | 修改版本号，不能与已有版本冲突 |
| `versionName` | `String` | 否 | 修改版本名称 |
| `forceUpdate` | `Boolean` | 否 | 修改强制更新标记 |
| `updateDesc` | `String` | 否 | 修改更新日志 |
| `downloadUrl` | `String` | 否 | 修改下载地址 |
 
### 请求示例
 
```bash
curl -X PUT http://localhost:5000/api/wbtools_version/3 \
  -H "Content-Type: application/json" \
  -d '{
    "versionName": "v2.4.1",
    "forceUpdate": true
  }'
```
 
### 成功响应
 
```
HTTP/1.1 200 OK
Content-Type: application/json
```
 
```json
{
  "id": 3,
  "versionCode": 13,
  "versionName": "v2.4.1",
  "forceUpdate": true,
  "updateDesc": "新增功能B，优化界面性能",
  "downloadUrl": "https://example.com/app-v2.4.0.apk",
  "createdAt": "2026-06-04T08:00:00Z",
  "updatedAt": "2026-06-04T09:30:00Z"
}
```
 
### 失败响应
 
**版本不存在（404）**
 
```
HTTP/1.1 404 NOT FOUND
Content-Type: application/json
```
 
```json
{
  "error": "版本不存在"
}
```
 
**版本号冲突（409）**
 
```
HTTP/1.1 409 CONFLICT
Content-Type: application/json
```
 
```json
{
  "error": "versionCode 13 已存在"
}
```
 
**参数校验错误（400）**
 
```
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json
```
 
```json
{
  "error": "versionCode 必须为正整数"
}
```
 
---
 
## 5. 删除版本
 
> 删除指定版本。操作不可撤销。
 
### 请求
 
```
DELETE /api/wbtools_version/{id}
```
 
### 路径参数
 
| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | `Long` | 版本唯一标识，从列表接口获取 |
 
### 请求示例
 
```bash
curl -X DELETE http://localhost:5000/api/wbtools_version/3
```
 
### 成功响应
 
```
HTTP/1.1 204 NO CONTENT
```
 
响应体为空。
 
### 失败响应
 
```
HTTP/1.1 404 NOT FOUND
Content-Type: application/json
```
 
```json
{
  "error": "版本不存在"
}
```
 
---
 
## 附录：错误码说明
 
| HTTP 状态码 | 含义 | 常见场景 |
|-------------|------|----------|
| `200` | 请求成功 | 查询、更新 |
| `201` | 创建成功 | 新增版本 |
| `204` | 删除成功，无响应体 | 删除版本 |
| `400` | 请求参数校验失败 | 缺少必填字段、字段格式错误 |
| `404` | 资源不存在 | 指定 `id` 的版本未找到、无版本记录 |
| `409` | 资源冲突 | `versionCode` 与已有版本重复 |
| `500` | 服务器内部错误 | 文件写入失败等 |
 
---
 
> 文档版本：v1.0 / 最后更新：2026-06-04
