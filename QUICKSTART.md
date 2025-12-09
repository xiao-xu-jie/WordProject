# Smart Vocab 快速开始指南

## 项目概述

Smart Vocab (智能词汇锻造场) 是一个基于 FastAPI 的智能词汇学习平台，集成了:
- OCR 文字识别 (PaddleOCR)
- AI 内容增强 (OpenAI/DeepSeek)
- SuperMemo-2 间隔重复算法
- 异步任务处理 (Celery)

## 已完成的功能

### ✅ Phase 1: 基础架构
- [x] 项目结构搭建
- [x] 配置管理 (Pydantic Settings)
- [x] 数据库连接 (SQLAlchemy Async)
- [x] Docker Compose 配置

### ✅ Phase 2: 数据库模型
- [x] User (用户表)
- [x] Book (词书表)
- [x] Word (单词表，支持 JSONB)
- [x] UserProgress (学习进度，SM-2 算法字段)
- [x] UserStudyPlan (学习计划)
- [x] UserFeedback (用户反馈)
- [x] CeleryTask (任务追踪)

### ✅ Phase 3: 认证模块
- [x] JWT 令牌生成和验证
- [x] 用户注册 API
- [x] 用户登录 API
- [x] 令牌刷新 API
- [x] 权限依赖 (get_current_user, get_current_admin_user)

### ✅ Phase 4: 学习系统
- [x] SuperMemo-2 算法实现
- [x] 获取学习会话 API (待复习 + 新单词)
- [x] 提交学习结果 API (自动计算下次复习时间)
- [x] 学习统计 API

## 快速启动

### 1. 安装依赖

```bash
# 激活虚拟环境
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件:

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://vocab_user:vocab_password_2024@localhost:5432/smart_vocab

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# OpenAI (可选，用于 AI 增强)
OPENAI_API_KEY=your-openai-api-key

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 3. 启动数据库

```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis

# 等待数据库就绪
docker-compose ps
```

### 4. 启动应用

```bash
# 启动 FastAPI 服务器
python main.py

# 或使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问 API 文档

打开浏览器访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 使用示例

### 1. 用户注册

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

响应:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_at": "2024-12-09T12:00:00Z",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "role": "user",
    "is_active": true,
    "subscription": "free",
    "created_at": "2024-12-09T11:00:00Z"
  }
}
```

### 2. 用户登录

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### 3. 获取学习会话

```bash
curl -X GET "http://localhost:8000/api/study/session?limit=20&include_new=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

响应:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "words": [
    {
      "word_id": 101,
      "spelling": "decorate",
      "phonetic": "/ˈdekəreɪt/",
      "definitions": [
        {"pos": "vt", "cn": "装饰; 点缀", "en": "make something look more attractive"}
      ],
      "sentences": [
        {"en": "They decorated the room with flowers.", "cn": "他们用花装饰了房间。"}
      ],
      "mnemonic": "de(加强) + cor(心) + ate → 用心装饰",
      "progress": {
        "status": 0,
        "ease_factor": 2.5,
        "interval": 0,
        "total_reviews": 0,
        "correct_count": 0
      }
    }
  ],
  "stats": {
    "total_due": 15,
    "new_words": 5,
    "review_words": 10
  }
}
```

### 4. 提交学习结果

```bash
curl -X POST "http://localhost:8000/api/study/submit" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "word_id": 101,
    "quality": 4,
    "time_spent": 5.2
  }'
```

响应:
```json
{
  "next_review_at": "2024-12-15T10:00:00Z",
  "interval": 6,
  "ease_factor": 2.6,
  "status": 2
}
```

### 5. 获取学习统计

```bash
curl -X GET "http://localhost:8000/api/study/stats?period=week" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## SuperMemo-2 算法说明

### 用户反馈评分

- **0 (Again)**: 完全不认识 → 重置进度，1天后复习
- **3 (Hard)**: 模糊记忆 → 降低难度因子
- **4 (Good)**: 认识但稍慢 → 正常增加间隔
- **5 (Easy)**: 秒杀 → 大幅增加间隔

### 算法参数

- **ease_factor**: 难度因子 (默认 2.5，范围 1.3-2.5)
- **interval**: 复习间隔 (天数)
- **repetitions**: 连续正确次数
- **next_review_at**: 下次复习时间

### 状态转换

- **0 (未学)**: 首次学习
- **1 (学习中)**: 评分 < 3
- **2 (复习中)**: 评分 = 3 或 4
- **3 (已掌握)**: 评分 >= 4 且已在复习中

## 数据库结构

### JSONB 字段示例

**definitions** (单词释义):
```json
[
  {
    "pos": "vt",
    "cn": "装饰; 点缀",
    "en": "make something look more attractive"
  },
  {
    "pos": "n",
    "cn": "勋章",
    "en": "medal"
  }
]
```

**sentences** (例句):
```json
[
  {
    "en": "They decorated the room with flowers.",
    "cn": "他们用花装饰了房间。"
  },
  {
    "en": "He was decorated for bravery.",
    "cn": "他因英勇而被授勋。"
  }
]
```

**history** (学习历史):
```json
[
  {
    "timestamp": "2024-12-09T10:00:00Z",
    "quality": 4,
    "time_spent": 5.2,
    "interval": 6,
    "ease_factor": 2.6
  }
]
```

## 待实现功能

### Phase 5: OCR 和 AI 集成
- [ ] PDF 上传和解析
- [ ] PaddleOCR 文字识别
- [ ] AI 数据清洗 (LLM)
- [ ] AI 内容增强 (生成例句和记忆法)

### Phase 6: Celery 异步任务
- [ ] Celery 配置
- [ ] PDF 解析任务
- [ ] AI 增强任务
- [ ] 任务进度追踪

### Phase 7: 管理后台
- [ ] 词书管理 API
- [ ] 用户管理 API
- [ ] 内容审核 API
- [ ] 系统监控 API

### Phase 8: 前端开发
- [ ] Vue 3 项目搭建
- [ ] 单词卡片组件
- [ ] 学习统计图表
- [ ] 管理后台界面

## 常见问题

### 1. 数据库连接失败

确保 PostgreSQL 已启动:
```bash
docker-compose ps
docker-compose logs postgres
```

### 2. 导入错误

确保所有 `__init__.py` 文件已创建:
```bash
# 检查文件结构
tree app
```

### 3. JWT 令牌无效

检查 `.env` 文件中的 `SECRET_KEY` 配置。

## 下一步

1. **添加测试数据**: 创建一些示例单词和词书
2. **实现 OCR 功能**: 集成 PaddleOCR
3. **开发前端**: 使用 Vue 3 创建用户界面
4. **部署**: 使用 Docker 容器化部署

## 技术支持

如有问题，请查看:
- API 文档: http://localhost:8000/docs
- 项目 README: README.md
- 设计文档: Smart Vocab (智能词汇锻造场) 设计文档.md
