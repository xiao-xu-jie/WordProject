# Smart Vocab (智能词汇锻造场)

一个基于 OCR + AI 的智能词汇学习平台，使用 SuperMemo-2 算法进行个性化复习。

## 项目结构

```
WordProject/
├── app/
│   ├── api/
│   │   └── endpoints/          # API 路由端点
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 应用配置
│   │   ├── database.py        # 数据库连接
│   │   └── security.py        # JWT 认证
│   ├── models/                 # 数据库模型
│   │   ├── user.py
│   │   ├── book.py
│   │   ├── word.py
│   │   ├── user_progress.py
│   │   ├── user_study_plan.py
│   │   ├── user_feedback.py
│   │   └── celery_task.py
│   ├── schemas/                # Pydantic 模式
│   ├── services/               # 业务逻辑
│   ├── tasks/                  # Celery 异步任务
│   └── utils/                  # 工具函数
├── tests/                      # 测试文件
├── uploads/                    # 上传文件目录
├── logs/                       # 日志目录
├── requirements.txt            # Python 依赖
├── .env.example               # 环境变量示例
├── docker-compose.yml         # Docker 配置
└── main.py                    # 应用入口

```

## 技术栈

- **后端**: FastAPI (Python 3.10+)
- **数据库**: PostgreSQL 15 (支持 JSONB)
- **缓存**: Redis 7
- **异步任务**: Celery + Redis
- **OCR**: PaddleOCR
- **AI**: OpenAI API / DeepSeek
- **对象存储**: MinIO (S3 兼容)

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的配置
```

### 3. 启动数据库服务

```bash
# 使用 Docker Compose 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head
```

### 5. 启动应用

```bash
# 启动 FastAPI 服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker (另一个终端)
celery -A app.tasks worker --loglevel=info

# 启动 Celery Beat (定时任务，另一个终端)
celery -A app.tasks beat --loglevel=info
```

## 核心功能模块

### 1. 认证模块 (Authentication)
- JWT 令牌认证
- 用户注册/登录
- 角色权限管理 (user/admin)
- 会员等级 (free/premium/enterprise)

### 2. 词书管理 (Book Management)
- PDF 上传
- OCR 文本识别 (PaddleOCR)
- AI 数据清洗 (LLM)
- 词汇入库

### 3. 学习系统 (Study System)
- SuperMemo-2 算法
- 学习会话管理
- 进度追踪
- 学习统计

### 4. AI 增强 (AI Enrichment)
- 自动生成例句
- 生成记忆技巧
- 内容质量评分

### 5. 管理后台 (Admin)
- 用户管理
- 内容审核
- 系统监控
- 任务管理

## API 文档

启动服务后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 数据库设计

### 核心表

1. **users** - 用户表
2. **books** - 词书表
3. **words** - 单词表 (使用 JSONB 存储多义项和例句)
4. **user_progress** - 用户学习进度 (SM-2 算法字段)
5. **user_study_plans** - 学习计划
6. **user_feedback** - 用户反馈
7. **celery_tasks** - 异步任务追踪

### JSONB 数据结构示例

**definitions** (单词释义):
```json
[
  {"pos": "vt", "cn": "装饰; 点缀", "en": "make something look more attractive"},
  {"pos": "n", "cn": "勋章", "en": "medal"}
]
```

**sentences** (例句):
```json
[
  {"en": "They decorated the room with flowers.", "cn": "他们用花装饰了房间。"},
  {"en": "He was decorated for bravery.", "cn": "他因英勇而被授勋。"}
]
```

## SuperMemo-2 算法

用户反馈评分:
- 0 (Again): 完全不认识
- 3 (Hard): 模糊记忆
- 4 (Good): 认识但稍慢
- 5 (Easy): 秒杀

算法会根据评分计算:
- 下次复习时间 (next_review_at)
- 难度因子 (ease_factor)
- 复习间隔 (interval)

## 开发路线图

### Phase 1: MVP (当前阶段)
- [x] 项目结构搭建
- [x] 数据库模型设计
- [x] 核心配置
- [ ] 认证 API
- [ ] 基础 CRUD API

### Phase 2: 核心功能
- [ ] OCR 集成
- [ ] AI 数据清洗
- [ ] SM-2 算法实现
- [ ] 学习会话 API

### Phase 3: 高级功能
- [ ] Celery 异步任务
- [ ] AI 内容增强
- [ ] 管理后台 API
- [ ] 文件上传 (MinIO)

### Phase 4: 前端
- [ ] Vue 3 项目搭建
- [ ] 单词卡片组件
- [ ] 学习统计图表
- [ ] 管理后台界面

### Phase 5: 部署
- [ ] Docker 容器化
- [ ] CI/CD 配置
- [ ] 监控和日志
- [ ] 性能优化

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_auth.py

# 生成覆盖率报告
pytest --cov=app tests/
```

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License

## 联系方式

项目链接: [https://github.com/yourusername/smart-vocab](https://github.com/yourusername/smart-vocab)
