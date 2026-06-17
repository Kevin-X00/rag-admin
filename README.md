# RAG Admin - 知识库管理系统

基于 FastAPI + ChromaDB + Vue3 的 RAG (检索增强生成) 后台管理系统。

## 功能概览

- **知识库管理** — 创建/编辑/删除知识库，独立配置（Embedding 模型、Chunk 大小、重叠等）
- **文档管理** — 上传文档（PDF/TXT/Markdown/DOCX），自动解析、分块、向量化
- **检索测试** — 在管理界面测试向量检索效果，查看相似度分数
- **问答测试** — 输入问题，系统执行 RAG 并返回 LLM 生成的答案
- **文档预览** — 查看原文内容与分块详情
- **统计分析** — 系统总览面板，知识库文档数/向量块统计

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python FastAPI + SQLAlchemy |
| 向量数据库 | ChromaDB (本地持久化) |
| Embedding | 本地 sentence-transformers 或 OpenAI API |
| LLM | OpenAI 兼容 API (支持 DeepSeek/OpenAI 等) |
| 前端 | Vue3 + Element Plus |
| 存储 | SQLite (元数据) + ChromaDB (向量) |
| 部署 | Docker Compose |

## 快速启动

### 方式一：Docker Compose（推荐）

```bash
# 克隆项目
cd rag-admin

# 编辑 config.yaml 配置 LLM API Key
vim config.yaml

# 启动
docker compose up -d

# 访问 http://localhost:8000
```

### 方式二：本地开发

#### 后端

```bash
cd backend
pip install -r requirements.txt

# 安装本地 Embedding 模型依赖
pip install sentence-transformers

# 启动服务
uvicorn backend.main:app --reload --port 8000
```

#### 前端

```bash
cd frontend
npm install
npm run dev

# 访问 http://localhost:3000（自动代理 API 到 8000）
```

#### 生产构建

```bash
cd frontend
npm run build
# 构建后静态文件在 frontend/dist/
# FastAPI 会自动挂载该目录并提供前端页面
```

## 配置说明

编辑项目根目录下的 `config.yaml` 文件：

```yaml
# Embedding 配置
embedding_provider: "local"  # 或 "openai"
embedding_model: "BAAI/bge-small-zh-v1.5"

# LLM 配置（用于问答）
llm_provider: "openai"
llm_model: "deepseek-chat"
llm_api_key: "sk-your-api-key"
llm_api_base: "https://api.deepseek.com"

# 分块参数
default_chunk_size: 512
default_chunk_overlap: 64
default_top_k: 5
```

### 推荐 Embedding 模型

- **BAAI/bge-small-zh-v1.5**（384维，轻量中文，推荐）
- **shibing624/text2vec-base-chinese**（768维）
- **shibing624/text2vec-large-chinese**（1024维，效果更好但更慢）

## API 文档

启动后端后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/health | 健康检查 |
| GET | /api/knowledge-bases | 知识库列表 |
| POST | /api/knowledge-bases | 创建知识库 |
| PUT | /api/knowledge-bases/{id} | 更新知识库 |
| DELETE | /api/knowledge-bases/{id} | 删除知识库 |
| GET | /api/documents | 文档列表 |
| POST | /api/documents/upload | 上传文档 |
| POST | /api/documents/{id}/process | 处理文档（分块+向量化） |
| POST | /api/search/retrieve | 向量检索测试 |
| POST | /api/search/qa | RAG 问答 |
| POST | /api/search/qa/stream | 流式 RAG 问答 |
| GET | /api/stats/overview | 系统总览统计 |

## 项目结构

```
rag-admin/
├── backend/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # SQLite 数据库操作
│   ├── models.py            # Pydantic 数据模型
│   ├── vectordb.py          # ChromaDB 操作
│   ├── document.py          # 文档解析与分块
│   ├── rag_chain.py         # RAG 问答链
│   ├── routes/
│   │   ├── knowledge_base.py
│   │   ├── documents.py
│   │   ├── search.py
│   │   └── stats.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue          # 主布局
│   │   ├── main.js          # 入口
│   │   ├── style.css        # 全局样式
│   │   ├── router/          # 路由配置
│   │   ├── api/             # API 调用
│   │   └── views/           # 页面组件
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── config.yaml              # 配置文件
├── docker-compose.yml       # Docker Compose
├── Dockerfile               # Docker 镜像
├── uploads/                 # 上传文件目录
├── data/                    # 数据目录
└── README.md
```

## License

MIT
