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
### 复制功能
- 微信小程序使用 `wx.setClipboardData` API 实现复制
- 需要为每条消息添加复制按钮

### Markdown 渲染
- 小程序原生不支持 Markdown
- 可使用第三方库如 `towxml`、`wechat-markdown` 或自行解析
- 需要考虑性能包体积
## Visual/Browser Findings
<!-- Multimodal content must be captured as text immediately -->
-

---
*Update this file after every 2 view/browser/search operations*
*This prevents visual information from being lost*
