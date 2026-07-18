# 工业时序异常诊断 Agent 平台（Relation-EVGAT Demo）

本项目集成 Relation-EVGAT 异常检测、DeepSeek 诊断编排、DashScope/Qwen 文档分析、Chroma 知识检索、Kimi 表格分析以及 Qwen LoRA 微调能力。

## 环境准备

```powershell
.venv\Scripts\activate
python -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

`.env` 只用于本机配置，禁止提交到 Git。每位开发者可仅填写自己负责链路所需的变量，其他变量保持为空。

## 模型与密钥配置

三条生成链路必须使用独立变量名。即使 DeepSeek 与 Qwen 使用同一个物理 DashScope API Key，也应分别填写到对应字段，因为二者的模型名和 Base URL 不同。

| 功能链路 | 环境变量前缀 | 模型 | 说明 |
|---|---|---|---|
| DeepSeek 工业诊断 | `DIAGNOSIS_AGENT_*` | `deepseek-v4-pro` | 实时监控、关系退化、根因分析和诊断报告 |
| PR #6 文档与知识分析 | `DOCUMENT_AGENT_*` | `qwen-plus` | 文档信息抽取、知识处理及相关维护脚本 |
| PR #8 Excel/CSV Agent | `TABLE_AGENT_KIMI_*` | `kimi-k2.6` | SQL 生成、查询解释和可视化规划 |
| 向量检索 | `EMBEDDING_*` | `text-embedding-v4` | Chroma 文本向量化；未单独填写时只复用 `DOCUMENT_AGENT_*` |

完整示例：

```dotenv
# DeepSeek 诊断链路
DIAGNOSIS_AGENT_PROVIDER=dashscope
DIAGNOSIS_AGENT_MODEL=deepseek-v4-pro
DIAGNOSIS_AGENT_API_KEY=填写项目的_DashScope_Key
DIAGNOSIS_AGENT_BASE_URL=填写当前有效的_DeepSeek_兼容接口
DIAGNOSIS_AGENT_REASONING_EFFORT=high

# PR #6：Qwen 文档与知识链路
DOCUMENT_AGENT_PROVIDER=dashscope
DOCUMENT_AGENT_MODEL=qwen-plus
DOCUMENT_AGENT_API_KEY=填写_PR6_使用的_Key
DOCUMENT_AGENT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# PR #8：Kimi 表格 Agent
TABLE_AGENT_KIMI_API_KEY=填写_PR8_使用的_Key
TABLE_AGENT_KIMI_BASE_URL=https://api.moonshot.cn/v1
TABLE_AGENT_KIMI_MODEL=kimi-k2.6

# 向量库
RAG_USE_CHROMA=true
RAG_VECTOR_PROVIDER=chroma
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
RAG_CHUNK_SIZE=700
RAG_CHUNK_OVERLAP=90
RAG_TOP_K=4
```

`EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL` 为空时，仅复用 `DOCUMENT_AGENT_API_KEY` 和 `DOCUMENT_AGENT_BASE_URL`。诊断链路不会被当作 Embedding 的隐式回退。旧版通用模型环境变量已停用，所有环境均必须使用上述服务专用变量。

### 密钥安全

- 不得提交 `.env`、PAT、Access Token 或数据库密码。
- PR #6 曾在 Git 历史中包含过 `.env`。即使当前分支删除该文件，历史中的 Key 仍可能被读取，因此相关 Key 必须在服务端撤销并重新生成。
- 如果同一个 DashScope Key 同时授权 DeepSeek、Qwen 和 Embedding，可在多个专用字段中填写同一值；代码不会用一个服务的模型名或 Base URL覆盖另一个服务。
- CI/CD 环境应在 GitHub Actions Secrets 中分别创建同名变量，不要把值写入工作流文件。

## 启动项目

后端：

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

访问 `http://127.0.0.1:5173/dashboard`。

## 主要页面

- `/dashboard`：实时监控、异常概览和诊断面板。
- `/relations`：关系图、退化边及传播路径。
- `/root-cause`：Top-K 根因候选及证据。
- `/diagnosis`：多源证据融合与 DeepSeek 诊断报告。
- `/table-analysis`：Excel/CSV 上传、Kimi SQL 生成及图表分析。
- `/knowledge`：Chroma 文档管理和语义检索。
- `/finetune`：Qwen LoRA 微调与评测。
- `/history`：诊断与文档处理历史。

## 模型对比实验

```powershell
.venv\Scripts\python.exe backend\benchmark_diagnosis_models.py --execute
.venv\Scripts\python.exe backend\make_model_benchmark_figures.py
```

实验产物输出至 `outputs/model_benchmark/`。当前自动指标主要评估结构完整性、证据覆盖、引用精确率、幻觉数量、延迟和 Token 消耗；在补充人工标注前，不应将其表述为根因诊断准确率。