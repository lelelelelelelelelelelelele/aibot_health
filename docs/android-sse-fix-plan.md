# Android 小程序 SSE 流式响应修复 - 手动实施计划

Status: In Progress (Backend Implemented)  
Last Updated: 2026-03-04

## 进度更新（2026-03-04）

- [x] 后端 SSE 支持已实现（服务端可返回流式数据）。
- [x] 代理层修复方案已落文档（HTTP/1.1 + 禁缓冲 + 禁 gzip）。
- [ ] Android 真机回归验证（Wi-Fi / 4G / 弱网）待完成。
- [ ] 前端侧 `onChunkReceived` 触发稳定性待复核。
- [ ] 发布前回归结论待写入 `miniprogram/docs/status/2026-03-04-status.md`。

## 问题背景

在"小愈助手"AI 对话功能中，流式输出（打字机效果）在 **Android 实机** 上完全失效：
- 发送后界面卡在"正在思考..."，无任何字符输出
- 等待十几秒后，整段回答瞬间全部出现

**根因**：微信 Android 端底层网络库与 HTTP/2 协议及 Nginx 代理缓冲共同作用导致的兼容性问题。

---

## 实施步骤

### 步骤 1：登录宝塔面板

1. 打开浏览器访问宝塔面板地址：`https://你的服务器IP:8888`
2. 使用账号密码登录

### 步骤 2：定位网站配置

1. 点击左侧菜单【网站】
2. 找到 `api.cpagz.com`（API 域名）
3. 点击对应行的【设置】按钮

### 步骤 3：修改 Nginx 配置

1. 在弹出窗口中选择【配置文件】标签
2. **在原有配置下方添加**以下 SSE 专用配置（不要删除原有内容）：

```nginx
    # ==================== SSE 流式接口专用配置 ====================
    # 匹配所有流式API路径：/knowledge_base/... /chat/... /v1/chat/... /v1/completions/...
    location ~ ^/(knowledge_base|chat|v1/chat|v1/completions) {
        proxy_pass http://127.0.0.1:7861;  # 后端服务地址

        # 1. 强制使用 HTTP/1.1（关键：规避 HTTP/2 帧机制问题）
        proxy_http_version 1.1;
        proxy_set_header Connection "";

        # 2. 彻底关闭 Nginx 缓冲（关键）
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;

        # 3. 关闭 gzip 压缩（压缩会破坏流式边界）
        gzip off;

        # 4. 优化超时设置（防止长连接被切断）
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        send_timeout 300s;

        # 5. 保持原始请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    # ==================== SSE 配置结束 ====================
```

**⚠️ 重要提示**：
- 上面的 `proxy_pass http://127.0.0.1:7861;` 是后端服务地址，如果不同请修改
- 这段配置应该添加在 `server { ... }` 块内部
- 确保它在 `location / { ... }` 之后，或者替换掉原有的 `location /knowledge_base` 配置

### 步骤 4：完整配置示例

修改后的配置文件大致如下：

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.cpagz.com;

    # SSL 证书配置（宝塔自动生成）
    ssl_certificate    /www/server/panel/vhost/cert/api.cpagz.com/fullchain.pem;
    ssl_certificate_key    /www/server/panel/vhost/cert/api.cpagz.com/privkey.pem;
    ssl_protocols TLSv1.1 TLSv1.2 TLSv1.3;

    # 默认根目录（可保留）
    root /www/wwwroot/api.cpagz.com;

    # ==================== 普通接口（保持默认）====================
    location / {
        proxy_pass http://127.0.0.1:7861;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ==================== SSE 流式接口专用配置 ====================
    location ~ ^/(knowledge_base|chat|v1/chat|v1/completions) {
        proxy_pass http://127.0.0.1:7861;

        # 强制 HTTP/1.1
        proxy_http_version 1.1;
        proxy_set_header Connection "";

        # 关闭缓冲
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;

        # 关闭 gzip
        gzip off;

        # 超时设置
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        send_timeout 300s;

        # 请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    # ==================== SSE 配置结束 ====================

    # 其他宝塔默认配置...
}
```

### 步骤 5：保存并重载 Nginx

1. 点击【保存】按钮
2. 宝塔会提示"是否重载 Nginx 服务"，点击【是】或【重载】
3. 等待 Nginx 重载完成（通常几秒钟）

---

## 配置要点说明

| 配置项 | 作用 | 必要性 |
|--------|------|--------|
| `proxy_http_version 1.1` | 强制使用 HTTP/1.1，避免 HTTP/2 帧机制问题 | ⭐ 必需 |
| `proxy_buffering off` | 关闭 Nginx 代理缓冲 | ⭐ 必需 |
| `proxy_cache off` | 关闭缓存 | ⭐ 必需 |
| `gzip off` | 关闭 gzip 压缩（压缩会破坏流式边界） | ⭐ 必需 |
| `chunked_transfer_encoding on` | 启用分块传输 | 建议 |
| `proxy_read_timeout 300s` | 延长读取超时，防止长连接被切断 | 建议 |

---

## 验证步骤

### 方法 1：命令行测试配置语法

SSH 连接到服务器，执行：

```bash
# 测试配置语法
nginx -t

# 如果提示命令找不到，使用宝塔的 nginx 路径
/www/server/nginx/sbin/nginx -t
```

### 方法 2：curl 测试 SSE 流式响应

```bash
# 测试 SSE 接口是否正常流式返回
curl -N -X POST https://api.cpagz.com/knowledge_base/local_kb/health%20clinic/chat/completions \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"model":"Qwen/Qwen3.5-397B-A17B","messages":[{"role":"user","content":"你好"}],"stream":true}'
```

**成功标志**：
- 字是一个一个蹦出来的，不是等很久后一次性出现
- 响应头中没有 `content-encoding: gzip`

### 方法 3：Android 真机测试

1. 打开微信小程序开发者工具
2. 点击【真机调试】→【调试设置】→开启【不校验合法域名】（测试用）
3. 用手机扫描二维码打开小程序
4. 发送一条消息，观察：
   - 是否能看到文字逐字出现（打字机效果）
   - 控制台中 `onChunkReceived` 回调是否正常触发

---

## 备选方案（如果主方案无效）

### 方案 B1：独立子域名

如果主域名的 HTTP/2 无法关闭，可以创建一个专门用于 SSE 的子域名：

1. 在宝塔【网站】中添加新站点 `sse.api.cpagz.com`
2. 配置文件中**去掉 `http2`**：

```nginx
server {
    listen 443 ssl;  # 注意：没有 http2
    server_name sse.api.cpagz.com;

    location / {
        proxy_pass http://127.0.0.1:7861;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        gzip off;
        # ... 其他配置同上
    }
}
```

3. 修改小程序代码 `miniprogram/src/config.ts`，将 API 地址改为 `https://sse.api.cpagz.com`

---

## 常见问题排查

### Q1: 配置保存后 Nginx 启动失败？

**检查**：
```bash
/www/server/nginx/sbin/nginx -t
```

**常见错误**：
- 括号不匹配：检查 `{` 和 `}` 是否成对
- 路径错误：确认 `proxy_pass` 的后端地址是否正确
- 重复 location：检查是否已有相同的 `location ~ ^/knowledge_base` 配置

### Q2: 配置生效但 Android 仍然不流式？

**排查步骤**：
1. 确认使用的是 `https://` 而不是 `http://`
2. 检查小程序代码中 `enableChunked: true` 是否设置（已设置 `enableHttp2: false`）
3. 尝试清除小程序缓存：开发者工具→【详情】→【本地缓存】→【清除缓存】
4. 检查后端是否正确返回 `Content-Type: text/event-stream`

### Q3: iOS 正常但 Android 不行？

这是预期的现象，正是此配置要解决的问题。如果配置后 Android 仍不行：
1. 确认 Nginx 已重载：`/www/server/nginx/sbin/nginx -s reload`
2. 检查响应头是否包含 `transfer-encoding: chunked`
3. 尝试在 Nginx 配置中添加 `X-Accel-Buffering: no` 响应头：

```nginx
add_header X-Accel-Buffering no;
```

---

## 影响范围

- ✅ **无需修改任何代码**
- ✅ 仅影响 SSE 流式接口，其他接口保持 HTTP/2 性能优势
- ⚠️ 需要 Nginx 重载（毫秒级服务中断）
- ✅ 所有使用 SSE 的客户端（Android、iOS、Web）都会受益
