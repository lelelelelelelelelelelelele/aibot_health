# Findings & Decisions

## Requirements
<!-- Captured from user request -->
- 增加一个前端，支持微信小程序接入
- 创建新分支进行开发
- 测试成功后合并到主分支

## Research Findings
<!-- Key discoveries during exploration -->
- 微信小程序原生开发需要分别编写 WXML/WXSS/JS，维护成本较高
- Taro (React) 更适合现有 Next.js/React 技术栈，可复用组件逻辑
- 现有前端使用 Ant Design Pro Chat，小程序需要使用原生组件或适配
- SSE 流式响应需要使用 wx.request + ArrayBuffer 处理
- 语音播放可使用 wx.createInnerAudioContext API

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 使用 Taro (React) 框架 | 现有前端使用 React/Next.js，Taro 可复用组件逻辑，生态成熟 |
| 聊天 + 语音播放 + 快捷问题 | 与现有 Web 端功能保持一致 |
| 共用 utils 工具函数 | speechManager.ts, errorHandler.ts 可通过适配器模式复用 |
| 共用后端 API | 现有 /knowledge_base/* 接口可直接使用，无需修改后端 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
|       |            |

## Resources
<!-- URLs, file paths, API references -->
-

## New Features: 复制与 Markdown 渲染

### 功能确认
1. **复制功能**: 每条 AI 回复消息旁边显示复制按钮，点击复制完整文本
2. **Markdown 渲染**: 使用 wechat-markdown 库完整渲染 Markdown 为富文本

### 技术选型：towxml
- **npm 包**: towxml
- **版本**: ^3.0.6
- **描述**: HTML、Markdown转WXML(WeiXin Markup Language)渲染库
- **安装命令**: `npm install towxml`
- **使用方式**:
  ```tsx
  import Towxml from 'towxml';
  const towxml = new Towxml();
  // 渲染 Markdown
  const result = towxml.toJson(markdownText, 'markdown');
  ```
- **注意事项**:
  - towxml 是小程序原生兼容的库
  - 需要将渲染结果转换为 Taro 组件

### 复制功能实现
- **API**: `wx.setClipboardData({ data: text })`
- **按钮位置**: 每条 assistant 消息的右下角
- **反馈**: 复制成功后显示 toast 提示

### 最终实现
- **依赖**: towxml ^3.0.6（最终选择，原计划 wechat-markdown 不存在）
- **组件**: MarkdownView.tsx - 使用 towxml 解析 Markdown 并渲染为 Taro 组件
- **复制**: 使用 Taro.setClipboardData API
- **构建**: 成功生成 dist 目录

### 提交记录
- a4382ec feat: add MarkdownView component using towxml for rendering markdown content
- 081c68e feat: add copy button and integrate MarkdownView for assistant messages
## Visual/Browser Findings
<!-- Multimodal content must be captured as text immediately -->
-

---
*Update this file after every 2 view/browser/search operations*
*This prevents visual information from being lost*
