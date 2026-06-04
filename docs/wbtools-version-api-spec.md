# WBTools 版本管理

## 1. 接口设计

### 1.1 获取所有历史版本（列表）

**接口地址**  
`GET /api/wbtools_version`

**返回数据结构**  
返回数组，每个元素包含：

| 字段        | 类型    | 说明                           |
| ----------- | ------- | ------------------------------ |
| id          | Long    | 唯一标识，用于编辑/删除        |
| versionCode | Integer | 版本号，用于排序与比较         |
| versionName | String  | 展示给用户的版本名称           |
| forceUpdate | Boolean | 强制更新标记（仅最新版本有效） |
| updateDesc  | String  | 更新日志全文，前端控制溢出     |
| downloadUrl | String  | APK 直链或下载落地页           |
| createdAt   | String  | 创建时间 (ISO 8601)            |
| updatedAt   | String  | 最后更新时间 (ISO 8601)        |

**排序**  
默认按 `versionCode` 降序返回（新版本在前）。可通过参数调整：  
`?sort=versionCode,asc` 升序。

**示例**  

```
GET /api/wbtools_version
```
```json
[
  {
    "id": 3,
    "versionCode": 12,
    "versionName": "v2.3.1",
    "forceUpdate": true,
    "updateDesc": "修复若干问题，优化性能...",
    "downloadUrl": "https://example.com/app-v2.3.1.apk",
    "createdAt": "2026-06-01T10:00:00Z",
    "updatedAt": "2026-06-03T12:00:00Z"
  }
]
```

---

### 1.2 获取最新版本（客户端升级检查）

**接口地址**  
`GET /api/wbtools_version/latest`

**返回数据结构**  
返回单个最新版本对象，字段同上（`forceUpdate` 在此处生效）。

**示例**  
```json
{
  "id": 3,
  "versionCode": 12,
  "versionName": "v2.3.1",
  "forceUpdate": true,
  "updateDesc": "修复若干问题，优化性能...",
  "downloadUrl": "https://example.com/app-v2.3.1.apk",
  "createdAt": "2026-06-01T10:00:00Z",
  "updatedAt": "2026-06-03T12:00:00Z"
}
```

---

### 1.3 新增版本

**接口地址**  
`POST /api/wbtools_version`

**请求体**  
```json
{
  "versionCode": 13,
  "versionName": "v2.4.0",
  "forceUpdate": false,
  "updateDesc": "新增功能A，修复B问题...",
  "downloadUrl": "https://example.com/app-v2.4.0.apk"
}
```
- `versionCode` 必须为正整数，且唯一。
- `versionName` 非空。
- `downloadUrl` 需符合 URL 格式。

**响应**  
201 Created，返回新创建的完整对象。

---

### 1.4 编辑版本

**接口地址**  
`PUT /api/wbtools_version/{id}`

**请求体**  
可部分更新，字段同新增。

**响应**  
200 OK，返回更新后的对象。

---

### 1.5 删除版本

**接口地址**  
`DELETE /api/wbtools_version/{id}`

**说明**  
前端必须弹出二次确认框，用户确认后发送请求。  
成功返回 204 No Content。

---

## 2. 数据约束

- `versionCode` 全局唯一，创建或更新时冲突返回 409 Conflict。
- `id` 为不可变唯一标识，由后端自动生成。
- 时间戳 `createdAt`、`updatedAt` 由后端自动维护。

---

## 3. 设置页面要求 (templates/settings.html)

### 3.1 配置入口

- 在设置页新增配置项 **WBTools Version**，对应 JSON 键 `wbtools_version`。
- 点击 **编辑** 按钮弹出历史版本管理弹窗，UI 与现有编辑弹窗保持一致。

### 3.2 弹窗展示

- 列表按 `versionCode` 降序排列（新版本在最上方）。
- 每项显示：
  - `versionName`（主文字）
  - `updateDesc`（灰色小字，单行超出末尾显示 `…`，通过 CSS `text-overflow: ellipsis` 实现）
- 点击截断文字可展开完整内容（或通过 Tooltip 展示）。

### 3.3 操作按钮

- 弹窗右上角增加：
  - **＋**（新增）按钮，点击进入空白新增界面。
  - **🗑**（删除）按钮，点击前需选中某一版本，弹出二次确认。
- 每个版本条目支持点击编辑，进入编辑界面（复用同一弹窗，内容变为表单，左上角显示返回箭头）。
- 返回箭头保留之前的滚动位置与上下文。

### 3.4 编辑界面

- 表单字段：`versionCode`、`versionName`、`updateDesc`、`downloadUrl`、`forceUpdate` 开关。
- 前端需校验格式（`versionCode` 正整数、URL 格式等）。
- 保存时调用对应接口，成功后刷新列表。

### 3.5 删除确认

- 点击删除按钮后弹出对话框：“确定删除该版本吗？此操作不可撤销。”
- 确认后发送 DELETE 请求，成功后移除该项。

---

## 4. 安全说明

- 个人项目，鉴权已通过其他方式处理，接口不额外增加权限校验。
