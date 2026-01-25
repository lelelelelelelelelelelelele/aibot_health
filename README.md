# 🌿 小愈助手 (Xiao Yu Assistant) - 智能健康小屋 RAG 系统

> **您好!我是“小愈助手”，由 [AI职工家庭健康小屋] 开发的智能健康顾问。**
> 我致力于为您提供专业、便捷的健康咨询服务，涵盖健康检测、养生产品、按摩理疗及会员权益等全方位指导。

---

## 🚀 项目概览

本项目是一个基于 **Langchain-Chatchat (v0.3.1)** 框架深度定制的 RAG (检索增强生成) 系统，结合了私有知识库与大语言模型，并配有现代化的前端交互界面。

### 🌟 核心价值
- **专业咨询**：基于本地精准 CSV/Markdown 知识库，拒绝幻觉。
- **完全私有**：支持本地部署，保障健康隐私数据不出域。
- **全端覆盖**：现代化的 Next.js 前端界面，适配多种设备。
- **闭环测试**：集成自动化 QA 测试集与相关性分析工具。

---

## 🛠️ 技术栈

### 后端 (Backend)
- **核心框架**：Langchain-Chatchat 0.3.1
- **嵌入模型**：DashScope `text-embedding-v4` (OneAPI 兼容)
- **大语言模型**：Qwen-max / Qwen3-max (OneAPI 托管)
- **向量数据库**：FAISS (L2 距离度量)
- **配置管理**：`data1` 目录下多维度 YAML 配置 (Model, KB, Prompt)

### 前端 (Frontend)
- **框架**：Next.js 14+ / Tailwind CSS
- **组件库**：Ant Design / **@ant-design/pro-chat**
- **特性**：流式响应 (SSE)、打字机效果、响应式布局

### QA 与运维 (DevOps)
- **测试框架**：Pytest
- **报告系统**：自定义 JSON & HTML 自动化测试报告
- **日志分析**：Log Relevance Extractor (用于优化检索相关性)

---

## 📂 项目结构

```text
aibot/
├── data1/               # 后端配置与数据核心
│   ├── data/            # 知识库源文件 (Markdown/CSV)
│   ├── basic_settings.yaml
│   ├── kb_settings.yaml
│   └── model_settings.yaml
├── frontend/            # Next.js 前端项目
│   └── src/app/page.tsx # 基于 ProChat 的聊天主页
├── tests/               # 自动化测试套件
│   ├── test_kb_chat.py  # RAG 接口集成测试
│   ├── kb_chat_request.yaml # 测试参数化配置
│   └── test_log_relevance_extractor.py # 相似度得分抽效
├── main.py              # 项目入口
└── README.md
```

---

## 🧪 自动化测试与质量检验

### 1. 核心 QA 测试集
针对 5 类典型考题（查价、方案咨询、会员逻辑、兜底问答、多轮对话）进行自动化验证。

**执行测试：**
```bash
# 运行所有 KB 测试并生成 HTML 报告
set KB_CHAT_GENERATE_REPORT=true
pytest tests/test_kb_chat.py -s
```

### 2. 相关性分析 (Similarity Analytics)
通过 `tests/test_log_relevance_extractor.py` 提取后台日志中的相似度得分，优化 `score_threshold` 设置。
> **当前最佳实践**：针对 DashScope v2 嵌入模型，建议 `score_threshold` 设为 **0.1 - 0.5**。

---

## 🖥️ 快速启动

### 第一步：后端服务启动
1. 确保 OneAPI/DashScope API Key 已配置在 `data1/model_settings.yaml`。
2. 启动服务：
```bash
chatchat start -a
```

### 第二步：前端界面启动
```bash
cd frontend
npm install
npm run dev
```
访问 `http://localhost:3000` 即可与 **小愈助手** 对话。

---

## 📍 知识库管理建议

为了保证“小愈助手”的精准性，建议将知识库按以下逻辑分类存放于 `data1/data/knowledge_base/`：
- `services/`: 核心服务清单（检测/按摩/理疗）
- `products/`: 养生药与健康产品
- `membership/`: 会员等级与促销活动

---

## 📝 开发者备注
- **阈值提醒**：若发现 AI 回答“未找到知识”，请检查 `tests/kb_chat_request.yaml` 中的 `score_threshold`。
- **环境隔离**：配置文件目前统一存放于 `data1` 根目录，启动时通过指定 `CHATCHAT_ROOT` 指向该文件夹。

---
> **AI 职工家庭健康小屋**  
> *让专业健康服务，触手可及。*

---

## 🔌 API 接口与参数规范

系统后端兼容 OpenAI 接口协议，但针对 RAG 场景扩展了 `extra_body` 参数集。

### 1. 请求体结构 (Request Body)
通过 `/chat/knowledge_base_chat` 接口发送请求时，核心参数如下：

```python
# 核心请求参数示例
payload = {
    "model": "qwen3-max",         # 使用的大模型名称
    "messages": [                 # 历史对话与当前问题
        {"role": "user", "content": "AI天眼多少钱？"}
    ],
    "stream": True,               # 启用流式响应
    "extra_body": {               # 🔴 RAG 核心扩展参数
        "top_k": 3,               # 匹配的知识块数量
        "score_threshold": 0.1,   # 相似度阈值 (0-2之间)
        "temperature": 0.7,       # 模型随机性
        "prompt_name": "health",  # 使用的 Prompt 模版名称
        "return_direct": False    # 是否直接返回知识库原文
    }
}
```

### 2. 流式响应处理 (Streaming)
后端返回 standard SSE 流。特殊的逻辑是：**首个数据块**通常包含检索到的知识库文档参考 (`docs`)。

```python
# 处理逻辑示例
for chunk in response:
    # 1. 解析首个 chunk 获取参考文档
    if first_chunk:
        references = chunk.docs  # 提取相关文档片段
        # 更新 UI 显示参考资料...
        
    # 2. 后续 chunk 为实时生成文本
    content = chunk.choices[0].delta.content
    # 实时追加到聊天框...
```

---

## 📚 知识库构建与工程化指南

为了确保“小愈助手”在大模型推理能力有限的情况下依然能提供精准、结构化的回答，我们推荐采用 **“半自动化知识蒸馏”** 方案进行数据准备。

### 🏗️ 整体架构图
```text
用户接口层 (Next.js/WeChat) → 检索增强层 (FAISS/RAG) → 知识库层 (Structured JSON) → 生成响应层 (Qwen)
```

### 🏭 知识蒸馏流水线 (Pipeline)
我们不直接投喂原始 PDF/Word，而是经过三层加工，确保“垃圾进，黄金出”。

| 阶段 | 工具 | 任务 | 产出物 |
| :--- | :--- | :--- | :--- |
| **L1 粗炼** | **NotebookLM** | **阅读与聚合**：吃透说明书、SOP、宣传单，按主题提取信息，消除文档碎片化。 | 主题式纯文本摘要 (Markdown) |
| **L2 精炼** | **Qwen-Max** | **结构化映射**：严格按照 JSON Schema，将文本转换为机器可读的结构化数据。 | 标准化 JSON 代码块 |
| **L3 质检** | **人工质检** | **校验与入库**：检查价格、指标准确性，确保医学建议的安全性。 | 最终 `.json` 文件 (存入 `/knowledge`) |

### 🛠️ 执行步骤

#### 第一步：L1 粗炼 (推荐使用 NotebookLM)
将所有原始资料上传至 NotebookLM，提取核心信息：
- **Prompt 示例**：请阅读源文件，提取“健康检测”相关的价格、时长、设备及禁忌。

#### 第二步：L2 结构化转换 (JSON Schema)
将摘要转换为结构化 JSON。建议使用 Qwen-max 进行此操作，以保证语法准确性。

**核心 Schema 示例 (Core Services):**
```json
[
  {
    "service_id": "svc_001",
    "service_name": "AI天眼筛查",
    "description": "视网膜风险评估",
    "equipment": ["智能眼底相机"],
    "price_info": { "member": "47元", "non_member": "50元" },
    "quality_score": 4.5
  }
]
```

#### 第三步：人工质检与入库
1. **核对**：检查医学参数和价格准确性。
2. **存放**：将文件存入 `data1/data/knowledge_base/` 下对应的子目录。

### 💡 方案优势
1. **彻底解决 Context 丢失**：JSON 绑定确保价格、服务名永不分离。
2. **小模型友好**：显著提升 Qwen-4B 等小模型的回答准确率。

---

## 🛣️ 路线图 (Roadmap)
- [x] 基于 Next.js 的现代化聊天 UI
- [x] Pytest 自动化集成测试与 HTML 报告
- [ ] **Function Calling**：实时接入 SQLite 数据库动态查价。
- [ ] **多模态解析**：支持健康报告照片识别。

---

## 📬 支持与定制
如需一键部署脚本或模版定制，请通过 Issue 或项目维护者联系。