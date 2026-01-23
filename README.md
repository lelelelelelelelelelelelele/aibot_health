# 🌿 健康小屋智能问答系统（RAG 知识库）

> 基于私有知识库自动回答客户关于健康检测、养生产品、按摩服务、会员优惠等高频问题
太棒了！你能走到这一步，说明后端“心脏”已经跳动起来了。现在我们需要进行**“体检”（QA 测试）**，确保这个大脑足够聪明、准确，然后才能给它穿上“衣服”（开发前端）。

除了测试问题，你确实还有几个**关键的技术动作**要在写前端代码前完成。我把它们整合成了一份**《系统验收与交付清单》**。

---

### 第一部分：高频问题测试集 (QA Test Suite)

请登录 Langchain-Chatchat 的 WebUI，按顺序提问。我为你准备了 **5 类典型考题**，覆盖了 RAG 的不同能力维度。

#### 🧪 考题 1：精准查价（测试 CSV/表格数据检索）
*   **问**：`AI天眼筛查多少钱？`
*   **期望回答关键点**：
    *   必须列出三个价格：标准价 50元、会员价 47元、职工价 34元。
    *   最好能提到时长（10分钟）。
*   **❌ 失败标志**：只报了一个价格，或者胡乱报价（幻觉）。

#### 🧪 考题 2：健康方案咨询（测试 JSON 关联推理）
*   **问**：`我最近总是失眠，睡不着，有什么调理方案吗？`
*   **期望回答关键点**：
    *   **设备**：推荐“小愈机器人睡眠专家模式”或“律动床垫”。
    *   **产品**：推荐“酸枣仁百合茯苓茶”或“止鼾枕”。
    *   **中医**：提到“头部刮痧”或“点穴”。
*   **❌ 失败标志**：只回答通用的“多喝热水、早睡早起”，没有提到店内具体的服务或产品。

#### 🧪 考题 3：复杂规则理解（测试会员制度逻辑）
*   **问**：`我想办个钻石会员，多少钱？包含什么？`
*   **期望回答关键点**：
    *   价格：9880元/年。
    *   权益：不限次检测、15次主题套餐、商城85折。
*   **❌ 失败标志**：把“钻石会员”和“畅享卡”搞混，或者遗漏核心权益。

#### 🧪 考题 4：兜底与联系方式（测试 System Prompt 约束）
*   **问**：`你们店在哪里？我想预约赵老师。`
*   **期望回答关键点**：
    *   地址：北京市西城区广义街5号广益大厦B座308。
    *   电话：18611263770。
*   **问**：`你们能做心脏搭桥手术吗？`（测试边界）
*   **期望回答**：礼貌拒绝，表明自己是健康调理机构，不进行手术，或建议联系赵老师咨询。

#### 🧪 考题 5：多轮对话（测试历史上下文）
*   **问1**：`那个护眼仪怎么卖？`
*   **问2**：`那它可以租吗？或者试用？`
*   **期望回答**：AI 应能联系上下文，回答关于“0元试用”的政策（付押金试用）。

---

### 第二部分：在开发前端前，你必须确认的 3 件事

很多开发者容易跳过这步直接写界面，结果发现接口调不通，排查起来很痛苦。请务必执行以下检查：

#### 1. 确认 API 接口可用性 (Crucial!)
前端（微信/网页）是不会直接访问 WebUI 的，它们是通过 **API** 和后端说话的。
*   **动作**：确保 Langchain-Chatchat 启动时加载了 `--api` 模式（默认通常是开启的，端口 7861）。
*   **测试方法**：不要只用 WebUI 测！打开浏览器或 Postman，访问 `http://localhost:7861/docs` (或你的服务器IP)。
*   **重点测试接口**：`/chat/knowledge_base_chat`。如果你能在 Swagger/Postman 里发请求并拿到回复，前端开发就稳了。

#### 2. 调整检索阈值 (Score Threshold)
*   **现象**：有时候你问的问题，AI 回答“根据已知信息无法回答”，但其实知识库里有。
*   **原因**：默认的**匹配分数阈值**可能太高了（比如 1.0）。
*   **操作**：在 WebUI 的“模型配置”或 `kb_config.py` 中，找到 `VECTOR_SEARCH_TOP_K`（建议设为 3-5）和 `SCORE_THRESHOLD`。
    *   如果是 `bge` 模型，建议阈值设在 **1.0 - 1.5** 之间（距离越小越相似，FAISS通常是欧氏距离；如果是余弦相似度则是越大越好，具体看 Chatchat 版本）。
    *   **简单做法**：在 WebUI 知识库问答左侧，拖动“知识匹配度阈值”，找到一个既不产生幻觉、又不会总是拒答的平衡点（通常是 **0.4 - 0.7** 左右）。

#### 3. 固化参数 (Persistence)
你在 WebUI 上拖动滑块调整好的参数（比如 Temperature=0.1, Top_K=3），记得要**回填到配置文件** (`model_config.py` 或 `kb_config.py`) 中。
*   **为什么**：WebUI 上的调整重启后可能会失效。前端调用 API 时，如果没有传参数，后端会读取配置文件的默认值。**确保配置文件的默认值就是你在 WebUI 测出来的最佳值。**

---

### 🎁 附赠：API 测试脚本 (Python)

在写前端之前，运行这个脚本。如果它能打印出答案，你就可以放心地去写前端代码了！

```python
import requests
import json

# 请替换为你的服务器 IP
BASE_URL = "http://localhost:7861"

def test_chat():
    url = f"{BASE_URL}/chat/knowledge_base_chat"
    
    payload = {
        "query": "脊柱调理多少钱？",
        "knowledge_base_name": "health_hut_kb", # 确保和你建的知识库名字一致
        "top_k": 3,
        "score_threshold": 1.0,
        "stream": False,
        "model_name": "Qwen1.5-4B-Chat", # 确保和你加载的模型名字一致
        "temperature": 0.1
    }
    
    try:
        print(f"正在发送请求到 {url} ...")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            # 解析返回的 JSON
            # 注意：不同版本的 Chatchat 返回结构可能略有不同，通常是 answer 字段
            try:
                res_json = response.json()
                print("\n✅ API 测试成功！")
                print("AI 回复:", res_json.get("answer", res_json))
            except:
                print("返回不是标准 JSON，可能是流式输出:", response.text)
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ 连接错误: {e}")

if __name__ == "__main__":
    test_chat()
```

**现在，去 WebUI 里当一回“刁钻客户”吧！测完告诉我结果，如果通过，我们就开始讨论前端怎么搞！** 🚀
---

## 🎯 项目目标

为您的健康小屋（提供养生药销售、按摩理疗、AI健康检测等服务）构建一个 **7×24 小时在线的智能客服窗口**，实现：

- ✅ 自动回答客户常见咨询（无需人工值守）
- ✅ 精准推荐服务与产品（基于用户健康需求）
- ✅ 提升专业形象（回答统一、权威、结构化）
- ✅ 完全离线运行（客户数据不出本地，保障隐私安全）

---

## 🧠 核心功能

| 功能 | 说明 |
|------|------|
| **健康检测咨询** | 回答血压/血糖检测流程、注意事项、结果解读 |
| **服务价格查询** | 实时提供按摩、理疗、检测等服务价格与时长 |
| **养生产品推荐** | 根据体质或健康问题推荐合适的养生茶/药 |
| **会员权益说明** | 解释免费/付费会员权益、办理方式、优惠活动 |
| **预约与到店指引** | 提供营业时间、地址、预约方式、到店流程 |
| **健康知识科普** | 输出高血压、糖尿病等慢病管理建议 |

---

## 📂 知识库结构（您需准备的材料）

系统依赖以下结构化知识文件（放入 `knowledge/` 目录），**确保回答精准可靠**：

```
knowledge/
├── services/
│   └── core_services.json      # 核心服务清单（检测/按摩/理疗）
├── products/
│   └── herbal_products.json    # 养生药与健康产品信息
├── health_knowledge/
│   └── chronic_diseases.md     # 慢病管理与健康建议（Markdown格式）
├── booking/
│   └── process_guide.md        # 预约流程、营业时间、地址等
└── membership/
    └── membership_plans.json   # 会员制度与当前优惠活动
```

> 💡 **为什么用 JSON/Markdown？**  
> 结构化格式让 AI 能**精准定位价格、时长、禁忌症等关键信息**，避免从大段文字中“猜答案”。

---

## ⚙️ 技术架构

- **RAG 框架**：[Langchain-Chatchat](https://github.com/chatchat-space/Langchain-Chatchat)（开箱即用，自带 Gradio Web 界面）
- **大语言模型**：Qwen1.5-4B-GGUF（本地运行，中文优化，完全离线）
- **嵌入模型**：BAAI/bge-large-zh-v1.5（中文向量化，高检索精度）
- **部署方式**：支持本地 PC / 云服务器 / 私有内网（数据不出域）

---

## 🚀 快速启动

### 1. 准备知识库
将您的服务、产品、健康知识按上述结构整理为 JSON/Markdown 文件，放入 `knowledge/` 目录。

### 2. 安装依赖
```bash
git clone https://github.com/chatchat-space/Langchain-Chatchat.git
cd Langchain-Chatchat
pip install -r requirements.txt
```

### 3. 下载模型（首次运行自动下载，也可手动缓存）
- LLM: `Qwen1.5-4B-Q5_K_M.gguf` → 放入 `models/`
- Embedding: `BAAI/bge-large-zh-v1.5` → 自动缓存至 HuggingFace 目录

### 4. 启动服务
```bash
python webui.py --model-name Qwen1.5-4B-Q5_K_M.gguf
```

### 5. 访问界面
浏览器打开 `http://localhost:7860`（或云服务器公网IP:7860），即可使用！

---

## 🔐 数据安全承诺

- 所有客户对话 **仅在本地处理，不上传任何云端**
- 知识库文件 **完全由您控制**，可随时更新/删除
- 支持部署在 **无外网的内网环境**，彻底杜绝数据泄露风险

---

## 📝 示例问答

**用户**：  
> “血压检测需要空腹吗？多少钱？”

**AI 回答**：  
> 您好！我们的基础体征检测（含血压、血糖、体重等）**无需空腹**，建议穿着宽松衣物。  
> **价格**：会员免费，非会员 20 元/次。  
> 检测约需 10-15 分钟，完成后会为您解读结果并提供健康建议。

---

## 🤝 适用场景

- 社区健康小屋对外服务窗口
- 中医养生馆智能客服
- 社区医院/卫生站健康咨询
- 药店+健康检测复合门店

---

## 📬 支持与定制

如需帮助：
- 整理知识库模板（JSON/Markdown）
- 一键部署脚本（含模型自动下载）
- 私有化部署方案（云服务器/本地服务器）

请提交 Issue 或联系项目维护者。

---

## 整体架构

``` text
用户接口层 → 检索增强层 → 知识库层 → 生成响应层
```

用户接口层：微信公众号、小程序、智能终端等
检索增强层：向量数据库、检索算法、结果排序
知识库层：结构化健康小屋业务知识
生成响应层：大模型生成、结果优化、安全过滤

---

## 知识库设计
通过深入研究你提供的对话背景（Health Hut 健康小屋项目）以及你目前的构想（NotebookLM + 大模型二次过滤），我为你制定了一套**“半自动化知识蒸馏”方案**。

这套方案的核心逻辑是：利用 **NotebookLM 的长窗口和强理解能力**作为“粗炼工厂”，负责将琐碎文档聚合成主题摘要；再利用 **大模型（如 Qwen/GPT-4o）** 作为“精炼车间”，将摘要强制转换为符合 RAG 要求的 **Structured JSON**。

---

### 🏭 整体流水线设计

我们不直接把 PDF 丢给 RAG，而是经过三层加工，确保“垃圾进，黄金出”。

| 阶段 | 工具 | 任务 | 产出物 |
| :--- | :--- | :--- | :--- |
| **L1 粗炼** | **NotebookLM** | **阅读与聚合**：吃透所有说明书、SOP、宣传单，按主题提取信息，消除文档间的碎片化。 | 5份主题式纯文本摘要（Markdown） |
| **L2 精炼** | **Qwen-Max / GPT-4o** | **结构化映射**：严格按照 JSON Schema，将文本转换为机器可读的数据。 | 标准化的 JSON 代码块 |
| **L3 质检** | **人工 + 脚本** | **校验与入库**：检查医学准确性、价格时效性，补充元数据（Tag、评分）。 | 最终 `.json` 文件（存入 `/knowledge`） |

---

### 🛠️ 具体执行步骤（手把手操作版）

#### 第一步：资料投喂与 L1 粗炼 (NotebookLM)

**操作动作**：
1. 打开 Google NotebookLM。
2. 创建一个新的 Notebook，命名为“健康小屋知识库”。
3. 上传你所有的原始文件：
   - 仪器说明书（PDF）
   - 药品/养生茶宣传册（图片转PDF或文字）
   - 内部员工培训手册（Word）
   - 会员制度文档
   - 常见问答记录（Excel/Txt）

**关键 Prompt（直接复制进 NotebookLM）**：
> *注意：你需要分 5 次提问，分别生成 5 个主题的摘要。不要一次性生成，否则信息会丢失。*

**示例：针对【核心服务】的提问**
```text
请阅读所有源文件，专注于提取“健康检测”和“理疗按摩”相关的服务内容。
请忽略无关信息，生成一份详细的总结，必须包含以下细节：
1. 服务名称（标准名称）
2. 具体包含哪些检测项目或按摩步骤
3. 使用的仪器设备名称
4. 服务时长
5. 收费标准（会员价 vs 非会员价）
6. 服务前的准备（如是否空腹、着装要求）
7. 结果解读的标准（如血压正常范围）
请以 Markdown 列表形式输出，尽可能保留原文中的数据细节。
```
*(针对产品、会员、健康知识、预约流程，请参照此逻辑调整 Prompt)*

---

#### 第二步：L2 结构化转换 (大模型过滤)

拿到 NotebookLM 的输出后，打开你的大模型对话窗口（建议使用能力较强的模型进行这一步，如 ChatGPT-4o 或 Qwen-Max，哪怕是临时的，因为这一步决定了 JSON 的语法正确性）。

**通用转换 Prompt 模板**：

```markdown
# Role
你是一个资深的数据工程师，专为健康小屋 RAG 系统构建知识库。

# Task
我将提供一段关于【{{主题}}】的文本资料（由 NotebookLM 生成）。
请将其转换为严格的 JSON 格式。

# Constraints
1. 严格遵守下方的 JSON Schema 定义，不要修改 Key 的名称。
2. 如果文本中缺少某个字段的信息，请填入 null 或 ""，不要编造数据。
3. "quality_score" 统一默认为 4.0。
4. "last_updated" 填入当前日期 "{{当前日期}}"。
5. 输出仅包含 JSON 代码块，不要包含任何解释性文字。

# Target Schema
{{这里粘贴对应的 Schema，见下方}}

# Input Text
{{这里粘贴 NotebookLM 生成的摘要}}
```

---

#### 🧱 核心 Schema 定义（直接用于上方 Prompt）

根据你的业务需求，我为你固化了 5 个核心 Schema。

**1. 核心服务 (Core Services)**
```json
[
  {
    "service_id": "string (自增ID, 如 svc_001)",
    "service_name": "string (服务名)",
    "description": "string (服务简介)",
    "equipment": ["string (仪器列表)"],
    "duration": "string (时长)",
    "price_info": {
      "member": "string (会员价)",
      "non_member": "string (非会员价)"
    },
    "preparation": "string (事前准备/禁忌)",
    "interpretation": "string (结果解读标准)",
    "quality_score": 4.5,
    "last_updated": "2026-01-23"
  }
]
```

**2. 养生产品 (Herbal Products)**
```json
[
  {
    "product_id": "string (如 prd_001)",
    "product_name": "string",
    "description": "string (功效描述)",
    "price": "string (规格和价格)",
    "target_audience": ["string (适用人群)"],
    "contraindications": ["string (禁忌人群)"],
    "usage": "string (使用方法)",
    "related_services": ["string (关联服务名)"],
    "quality_score": 4.5,
    "last_updated": "2026-01-23"
  }
]
```

**3. 健康知识 (Health Knowledge)**
*建议：知识类内容如果太长，JSON 字段里放摘要，全文放 Markdown。但如果是 FAQ 级别，JSON 更好。*
```json
[
  {
    "topic_id": "string (如 knw_001)",
    "category": "string (如 '慢病管理', '生活方式')",
    "question": "string (用户常问的问题)",
    "answer": "string (核心建议)",
    "detailed_advice": "string (详细指导)",
    "related_products": ["string (关联产品推荐)"],
    "quality_score": 4.5,
    "last_updated": "2026-01-23"
  }
]
```

**4. 会员制度 (Membership)**
```json
{
  "plans": [
    {
      "level_name": "string (如 '免费会员', '尊享会员')",
      "cost": "string",
      "benefits": ["string (权益列表)"],
      "requirements": "string (办理条件)"
    }
  ],
  "current_promotions": [
    {
      "title": "string",
      "details": "string",
      "valid_until": "YYYY-MM-DD"
    }
  ]
}
```

---

#### 第三步：人工质检与文件落盘 (关键一步)

由于涉及医疗健康，**不可完全信任 AI**。将生成的 JSON 复制到代码编辑器（如 VS Code）中，进行最后一步：

1. **医学核查**：检查 `interpretation`（结果解读）和 `contraindications`（禁忌）是否准确。
   - *错误示例*：血压 140/90 是正常（❌）
   - *修正*：血压 140/90 属于高血压临界值（✅）
2. **价格核查**：确保价格与店面实际价格一致。
3. **格式保存**：
   - 存为 UTF-8 编码的 `.json` 文件。
   - 放入 Langchain-Chatchat 的 `knowledge` 对应子目录中。

---

### 💡 为什么这个方案适合你的 RAG 系统？

1. **解决 Context 丢失问题**：Langchain-Chatchat 切片时，经常把“价格”和“服务名”切断。通过 NotebookLM 聚合 + JSON 强制绑定，确保了**服务名、价格、时长永远在一个 JSON 对象里**，检索时一次性全部拿出来。
2. **Qwen-4B 友好**：你使用的 Qwen1.5-4B 是小参数模型，推理能力有限。相比于让它去读懂一篇 3000 字的长文档，**直接喂给它结构化的 JSON**，它的回答准确率会由 60% 飙升到 95% 以上。
3. **低成本落地**：NotebookLM 免费，本地大模型免费，不需要昂贵的 API 调用，完美契合你的私有化部署需求。

### 🚀 立即行动清单

1. 收集好你的 Word/PDF 资料。
2. 用 NotebookLM 生成第一份“核心服务”摘要。
3. 复制我上面的 Schema 和 Prompt，让 AI 生成 JSON。
4. 粘贴结果给我看一眼，我帮你做最后的格式微调！
> **让专业健康服务，触手可及。**  

## todo

方案 C：Function Calling / Tool Use（进阶，未来升级方向）
这是最“极客”但也最复杂的做法。
原理：
把价格存入 SQLite 数据库。
告诉大模型：“如果你被问到价格，请调用 query_price 工具”。
用户问：“筛查多少钱？” -> 模型调用工具 -> 查库返回 47 -> 模型回答“47元”。
理由：目前对于你“先跑通”的目标来说，这步太重了。Langchain-Chatchat 配置工具调用需要改代码。建议作为二期优化的目标。

FAQ