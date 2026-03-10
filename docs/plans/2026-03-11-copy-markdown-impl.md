# 微信小程序复制与 Markdown 渲染功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为微信小程序聊天页面添加复制按钮和 Markdown 完整渲染功能

**Architecture:** 使用 wechat-markdown 库解析 Markdown，使用 wx.setClipboardData API 实现复制按钮

**Tech Stack:** Taro (React), wechat-markdown, 微信小程序 API

---

## 文件修改清单
- Modify: `miniprogram/package.json` - 添加 wechat-markdown 依赖
- Modify: `miniprogram/src/pages/index/index.tsx` - 添加复制按钮和处理 Markdown 渲染
- Modify: `miniprogram/src/pages/index/index.scss` - 添加复制按钮样式

---

### Task 1: 安装 wechat-markdown 依赖

**Files:**
- Modify: `miniprogram/package.json`

**Step 1: 添加依赖到 package.json**

在 dependencies 中添加 `"wechat-markdown": "^0.3.0"`:

```json
"dependencies": {
  "@tarojs/components": "^4.1.11",
  "@tarojs/plugin-framework-react": "^4.1.11",
  "@tarojs/plugin-platform-weapp": "^4.1.11",
  "@tarojs/react": "^4.1.11",
  "@tarojs/runtime": "^4.1.11",
  "@tarojs/taro": "^4.1.11",
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "wechat-markdown": "^0.3.0"
},
```

**Step 2: 安装依赖**

Run: `cd miniprogram && npm install`

Expected: 安装成功，node_modules 中包含 wechat-markdown

---

### Task 2: 创建 Markdown 渲染组件

**Files:**
- Create: `miniprogram/src/components/MarkdownView.tsx`

**Step 1: 创建 MarkdownView 组件**

创建文件 `miniprogram/src/components/MarkdownView.tsx`:

```tsx
import { View, Text } from '@tarojs/components'
import WechatMarkdown from 'wechat-markdown'
import { useMemo } from 'react'
import './markdown-view.scss'

interface MarkdownViewProps {
  content: string
}

export default function MarkdownView({ content }: MarkdownViewProps) {
  const renderedContent = useMemo(() => {
    if (!content) return []
    const md = new WechatMarkdown()
    const result = md.render(content)
    // 解析渲染结果为节点数组
    return parseMarkdownNodes(result)
  }, [content])

  return (
    <View className='markdown-content'>
      {renderedContent.map((node, index) => (
        <RenderNode key={index} node={node} />
      ))}
    </View>
  )
}

interface Node {
  type: string
  tag?: string
  text?: string
  attrs?: Record<string, string>
  children?: Node[]
}

function parseMarkdownNodes(html: string): Node[] {
  // 简单解析：将 HTML 字符串转为节点对象
  // 这里使用一个简化实现
  const nodes: Node[] = []

  // 使用正则解析基本 HTML 结构
  const tagRegex = /<(\w+)([^>]*)>([\s\S]*?)<\/\1>/g
  const textRegex = /^<(\w+)([^>]*)>([\s\S]*)$/

  let match
  while ((match = tagRegex.exec(html)) !== null) {
    const tag = match[1]
    const attrsStr = match[2]
    const children = match[3]

    const attrs: Record<string, string> = {}
    const attrRegex = /(\w+)="([^"]*)"/g
    let attrMatch
    while ((attrMatch = attrRegex.exec(attrsStr)) !== null) {
      attrs[attrMatch[1]] = attrMatch[2]
    }

    // 处理子节点
    let childNodes: Node[] = []
    if (children.includes('<')) {
      childNodes = parseMarkdownNodes(children)
    } else if (children.trim()) {
      childNodes = [{ type: 'text', text: children }]
    }

    nodes.push({
      type: 'element',
      tag,
      attrs,
      children: childNodes
    })
  }

  // 处理纯文本
  if (nodes.length === 0 && html.trim()) {
    return [{ type: 'text', text: html }]
  }

  return nodes
}

function RenderNode({ node }: { node: Node }) {
  if (node.type === 'text') {
    return <Text>{node.text}</Text>
  }

  if (node.type === 'element' && node.tag) {
    const tag = node.tag.toLowerCase()
    const className = node.attrs?.class || ''

    // 处理代码块
    if (tag === 'pre' || tag === 'code') {
      return (
        <View className={`md-${tag} ${className}`}>
          {node.children?.map((child, i) => (
            <RenderNode key={i} node={child} />
          ))}
        </View>
      )
    }

    // 处理标题
    if (tag.startsWith('h')) {
      return (
        <View className={`md-${tag} ${className}`}>
          {node.children?.map((child, i) => (
            <RenderNode key={i} node={child} />
          ))}
        </View>
      )
    }

    // 处理列表
    if (tag === 'ul' || tag === 'ol') {
      return (
        <View className={`md-${tag} ${className}`}>
          {node.children?.map((child, i) => (
            <RenderNode key={i} node={child} />
          ))}
        </View>
      )
    }

    if (tag === 'li') {
      return (
        <View className={`md-${tag} ${className}`}>
          {node.children?.map((child, i) => (
            <RenderNode key={i} node={child} />
          ))}
        </View>
      )
    }

    // 处理加粗、斜体
    if (tag === 'strong' || tag === 'b') {
      return (
        <Text className='md-strong'>
          {node.children?.map((child, i) => (
            <RenderNode key={i} node={child} />
          ))}
        </Text>
      )
    }

    if (tag === 'em' || tag === 'i') {
      return (
        <Text className='md-em'>
          {node.children?.map((child, i) => (
            <RenderNode key={i} node={child} />
          ))}
        </Text>
      )
    }

    // 处理链接
    if (tag === 'a') {
      return (
        <Text className='md-link'>{node.children?.[0]?.text}</Text>
      )
    }

    // 处理段落
    if (tag === 'p') {
      return (
        <View className='md-p'>
          {node.children?.map((child, i) => (
            <RenderNode key={i} node={child} />
          ))}
        </View>
      )
    }

    // 其他标签
    return (
      <View className={`md-${tag} ${className}`}>
        {node.children?.map((child, i) => (
          <RenderNode key={i} node={child} />
        ))}
      </View>
    )
  }

  return null
}
```

**Step 2: 创建 MarkdownView 样式文件**

创建文件 `miniprogram/src/components/markdown-view.scss`:

```scss
.markdown-content {
  font-size: 14px;
  line-height: 1.6;
  color: #333;

  .md-p {
    margin-bottom: 8px;
  }

  .md-h1 {
    font-size: 20px;
    font-weight: bold;
    margin: 16px 0 8px;
  }

  .md-h2 {
    font-size: 18px;
    font-weight: bold;
    margin: 14px 0 6px;
  }

  .md-h3 {
    font-size: 16px;
    font-weight: bold;
    margin: 12px 0 4px;
  }

  .md-strong, .md-b {
    font-weight: bold;
  }

  .md-em, .md-i {
    font-style: italic;
  }

  .md-link {
    color: #1890ff;
    text-decoration: underline;
  }

  .md-pre, .md-code {
    background-color: #f5f5f5;
    border-radius: 4px;
    padding: 8px;
    font-family: monospace;
    font-size: 13px;
    overflow-x: auto;
    margin: 8px 0;
  }

  .md-ul, .md-ol {
    padding-left: 20px;
    margin: 8px 0;
  }

  .md-li {
    margin: 4px 0;
  }
}
```

**Step 3: Commit**

```bash
git add miniprogram/src/components/MarkdownView.tsx miniprogram/src/components/markdown-view.scss
git commit -m "feat: add MarkdownView component for rendering markdown content"
```

---

### Task 3: 添加复制按钮功能

**Files:**
- Modify: `miniprogram/src/pages/index/index.tsx`
- Modify: `miniprogram/src/pages/index/index.scss`

**Step 1: 在 index.tsx 中添加复制处理函数**

在 `handleVoicePlay` 函数后添加复制处理函数:

```tsx
const handleCopy = (text: string) => {
  Taro.setClipboardData({
    data: text,
    success: () => {
      Taro.showToast({
        title: '复制成功',
        icon: 'success',
        duration: 1500
      })
    },
    fail: () => {
      Taro.showToast({
        title: '复制失败',
        icon: 'error',
        duration: 1500
      })
    }
  })
}
```

**Step 2: 修改消息渲染，添加复制按钮**

找到消息渲染部分 (约第 511-520 行)，将:

```tsx
<View className='message-content'>
  <Text>{msg.content || (msg.role === 'assistant' && isGenerating && msg.id === messages[messages.length - 1].id ? '正在思考中...' : '')}</Text>
  {msg.role === 'assistant' && msg.content && (
    <View
      className='voice-btn'
      onClick={() => handleVoicePlay(msg.content)}
    >
      🔊
    </View>
  )}
</View>
```

修改为:

```tsx
<View className='message-content'>
  {msg.role === 'user' ? (
    <Text>{msg.content}</Text>
  ) : (
    <MarkdownView content={msg.content || (isGenerating && msg.id === messages[messages.length - 1].id ? '正在思考中...' : '')} />
  )}
  {msg.role === 'assistant' && msg.content && (
    <View className='message-actions'>
      <View
        className='action-btn copy-btn'
        onClick={() => handleCopy(msg.content)}
      >
        📋
      </View>
      <View
        className='action-btn voice-btn'
        onClick={() => handleVoicePlay(msg.content)}
      >
        🔊
      </View>
    </View>
  )}
</View>
```

**Step 3: 导入 MarkdownView 组件**

在文件顶部添加导入:

```tsx
import MarkdownView from '../../components/MarkdownView'
```

**Step 4: 添加复制按钮样式**

在 `index.scss` 中添加:

```scss
.message-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.action-btn {
  font-size: 14px;
  padding: 4px 8px;
  cursor: pointer;
}

.copy-btn {
  opacity: 0.7;

  &:hover {
    opacity: 1;
  }
}
```

**Step 5: Commit**

```bash
git add miniprogram/src/pages/index/index.tsx miniprogram/src/pages/index/index.scss
git commit -m "feat: add copy button for assistant messages"
```

---

### Task 4: 构建验证

**Step 1: 运行构建**

Run: `cd miniprogram && npm run build:weapp`

Expected: 构建成功，生成 dist 目录

**Step 2: 检查是否有编译错误**

如果出现 TypeScript 错误，根据错误信息修复

---

### Task 5: 测试验证

**Step 1: 在微信开发者工具中预览**

打开 `miniprogram/dist` 目录，使用微信开发者工具加载

**Step 2: 验证复制功能**
- 发送一条消息
- AI 回复后，检查复制按钮是否显示
- 点击复制按钮，验证 toast 提示
- 粘贴验证内容是否正确

**Step 3: 验证 Markdown 渲染**
- 发送一条会返回 Markdown 格式的问题（如"请列出3个健康建议"）
- 检查 Markdown 是否正确渲染（标题、列表等）

---

## 验收检查清单
- [ ] wechat-markdown 依赖安装成功
- [ ] MarkdownView 组件创建并正常工作
- [ ] 复制按钮显示在 AI 回复上
- [ ] 点击复制按钮可复制完整文本
- [ ] 复制成功显示 toast 提示
- [ ] Markdown 内容正确渲染
- [ ] 构建成功无错误
