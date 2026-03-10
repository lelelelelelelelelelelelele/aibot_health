# 设计文档：微信小程序复制与 Markdown 渲染功能

## 概述
为微信小程序聊天页面添加复制功能和 Markdown 完整渲染功能。

## 功能需求

### 1. 复制功能
- 每条 AI 回复消息旁边显示复制按钮
- 点击按钮复制完整消息文本
- 复制成功后显示 toast 提示

### 2. Markdown 渲染
- 使用 wechat-markdown 库解析 Markdown
- 支持 GFM (GitHub Flavored Markdown) 完整特性
- 包括：标题、列表、粗体、斜体、链接、代码块、表格等

## 技术方案

### 依赖选择
- **Markdown 库**: wechat-markdown (~50KB)
- **优势**: 轻量级、专为微信设计、GFM 支持

### 复制实现
- **API**: `wx.setClipboardData({ data: text })`
- **位置**: assistant 消息右下角

### Markdown 渲染实现
- 安装 wechat-markdown
- 渲染为 Taro 组件可识别的节点结构
- 配置 Taro 支持 HTML 标签

## 文件修改清单
1. `miniprogram/package.json` - 添加 wechat-markdown 依赖
2. `miniprogram/src/pages/index/index.tsx` - 添加复制按钮和 Markdown 渲染
3. `miniprogram/src/pages/index/index.scss` - 复制按钮样式

## 验收标准
- [ ] 复制按钮显示在每条 AI 回复上
- [ ] 点击复制按钮可复制完整文本
- [ ] 复制成功显示 toast 提示
- [ ] Markdown 内容正确渲染为富文本
- [ ] 常用 Markdown 格式（标题、列表、代码块等）显示正常
