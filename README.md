# 扫地机器人智能客服 Agent

基于 **RAG + ReAct 循环**的大模型智能客服系统，面向扫地机器人 / 扫拖一体机场景，提供专业问答、故障排查与个性化使用报告生成能力。

## 功能特性

- **RAG 知识库问答**：基于 FAISS 向量库 + 通义千问 Embedding 构建领域知识库，支持 PDF / TXT 文档入库，MD5 增量去重
- **ReAct 自主决策**：基于 LangChain `create_agent` 搭建，按「思考 → 行动 → 观察」循环自主决定是否调用工具、调用哪个工具
- **多工具协作**：内置 RAG 检索、天气、用户画像、外部使用记录等 7 个自定义工具
- **动态提示词切换**：通过中间件识别报告生成场景，自动切换「问答 / 报告」两套系统提示词
- **工具调用监控**：中间件统一记录工具入参与调用结果日志，异常可追溯
- **流式输出 + 多会话管理**：Streamlit 前端实现打字机式流式回复，支持会话新建 / 加载 / 删除 / 持久化
- **多轮对话记忆**：Agent 调用携带会话历史，多轮上下文不丢失

## 技术栈

Python 3.10 · LangChain / LangGraph · FAISS · DashScope（qwen-max + text-embedding-v3）· Streamlit · PyYAML

## 快速开始

### 1. 环境准备

```bash
pip install -r requirements.txt
```

配置 DashScope API Key 环境变量：

```bash
# Windows
set DASHSCOPE_API_KEY = 自己的key
```

### 2. 构建知识库

将领域文档（.txt / .pdf）放入 `data/` 目录，运行：

```bash
python rag/vector_store.py
```

脚本按文件 MD5 增量去重，索引保存在 `faiss_index/`。

### 3. 启动应用

```bash
streamlit run app_new.py
```

## 项目结构

```
├── app_new.py              # Streamlit 前端入口（聊天界面 + 会话管理）
├── agent/
│   ├── react_agent.py      # ReAct Agent 封装（流式执行，支持多轮历史）
│   └── tools/
│       ├── agent_tools.py  # 自定义工具集（RAG / 天气 / 用户画像 / 外部数据）
│       └── middleware.py   # 中间件：工具调用监控 + 动态提示词切换
├── rag/
│   ├── vector_store.py     # FAISS 向量库（文档加载、分片、入库、MD5 去重）
│   └── rag_service.py      # RAG 检索 + 总结链路
├── model/
│   └── factory.py          # 模型工厂（Chat / Embedding）
├── utils/                  # 路径、日志、配置、Prompt 加载等通用工具
├── config/                 # YAML 配置（模型、向量库、提示词路径）
├── prompts/                # 系统提示词（问答 / 报告 / RAG 总结）
└── data/                   # 领域知识文档 + 外部使用记录
```

## 配置说明

| 文件 | 说明 |
| --- | --- |
| `config/rag.yml` | 对话模型与 Embedding 模型名称 |
| `config/chroma.yml` | 向量库路径、分片参数（chunk_size / chunk_overlap）、检索 top-k |
| `config/prompts.yml` | 各提示词文件路径 |
| `config/agent.yml` | 外部数据文件路径 |
| `prompts/main_prompt.txt` | 智能客服主系统提示词 |
| `prompts/report_prompt.txt` | 报告生成场景提示词 |
| `prompts/rag_summarize.txt` | RAG 总结链路提示词 |

## 数据说明

- `data/` 下的领域文档用于构建 RAG 知识库（含故障排除、维护保养、选购指南等）
- `data/external/records.csv` 为外部系统使用记录（静态演示数据，覆盖 2025 年 1 - 12 月）
- 天气、用户位置、用户 ID 为演示用模拟数据，可替换为真实 API 实现

## 扩展方向

- 天气 / 位置工具接入真实 API（高德、和风天气等）
- 引入检索质量评估脚本与分片参数调优实验
- 补充单元测试与容器化部署
