# 项目名称：Smart Vocab (智能词汇锻造场)

**设计目标**：构建一个从非结构化文档（PDF）自动生成结构化题库，并基于记忆曲线进行个性化训练的SaaS平台。

## 核心价值主张

1. **智能化内容生成**：通过 OCR + AI 自动将传统词书转化为富媒体学习材料
2. **科学记忆算法**：基于 SuperMemo-2 算法的个性化复习计划
3. **数据资产积累**：用户学习数据可用于优化算法和生成学习报告
4. **可扩展架构**：支持未来扩展到其他学科（如专业术语、医学词汇等）

------

## 一、 系统总体架构 (System Architecture)

我们将采用 **微服务化思想的单体架构 (Modular Monolith)**，在初期降低部署难度，但保持模块清晰。

### 1. 逻辑架构图

代码段

```
graph TD
    User[用户端 (Web/Mobile)] --> API_Gateway[API 网关 / Nginx]
    Admin[管理员后台] --> API_Gateway
    
    subgraph "Backend Service (FastAPI)"
        Auth[认证模块 (JWT)]
        Study[刷题核心 (SRS算法)]
        Data_Center[数据管理模块]
        
        subgraph "ETL & AI Pipeline (异步任务)"
            Parser[PDF/OCR 解析器]
            Cleaner[数据清洗]
            AI_Enricher[AI 增强引擎 (生成例句/记忆法)]
        end
    end
    
    API_Gateway --> Auth
    API_Gateway --> Study
    API_Gateway --> Data_Center
    
    Data_Center -- 触发导入 --> Parser
    Parser --> Cleaner --> AI_Enricher
    
    AI_Enricher -- 存入 --> DB[(PostgreSQL)]
    Study -- 读写 --> DB
    Study -- 缓存 --> Redis[(Redis Cache)]
    
    File_Storage[对象存储 MinIO/S3] -- 存储PDF --> Parser
```

### 2. 核心技术栈选型

| **模块**     | **技术选型**                      | **理由**                                                     |
| ------------ | --------------------------------- | ------------------------------------------------------------ |
| **前端**     | **Vue 3 + TypeScript + Naive UI** | 开发效率高，组件库适合做数据展示和后台。                     |
| **后端**     | **Python FastAPI**                | 性能极高，原声支持异步（适合处理耗时的OCR和AI请求），Python生态拥有最强的OCR/NLP库。 |
| **数据库**   | **PostgreSQL**                    | **关键选型**。PG支持 `JSONB` 类型，非常适合存储单词的“例句”、“多义项”等非定长数据。 |
| **ORM**      | **SQLAlchemy (Async)**            | 现代Python ORM标准。                                         |
| **异步队列** | **Celery + Redis**                | PDF解析和AI增强是耗时操作，必须异步处理，不能阻塞主线程。    |
| **OCR引擎**  | **PaddleOCR**                     | 目前开源界中文/英文混合识别效果最好的轻量级引擎。            |
| **AI LLM**   | **OpenAI / DeepSeek API**         | 用于数据清洗和生成记忆技巧（Prompt Engineering）。           |

------

## 二、 详细数据库设计 (Schema Design)

这是系统的灵魂。为了支持你想要的“例句”和“记忆技巧”，我们需要精心设计 `words` 表。

### 1. 核心表结构

#### A. `users` (用户表 - 基础认证)

| **字段**                | **类型**  | **说明**                                   |
| ----------------------- | --------- | ------------------------------------------ |
| id                      | INT       | PK                                         |
| username                | VARCHAR   | 用户名 (唯一索引)                          |
| email                   | VARCHAR   | 邮箱 (唯一索引)                            |
| password_hash           | VARCHAR   | 密码哈希 (bcrypt)                          |
| role                    | ENUM      | `user`, `admin`                            |
| created_at              | TIMESTAMP | 注册时间                                   |
| last_login_at           | TIMESTAMP | 最后登录时间                               |
| is_active               | BOOLEAN   | 账号状态 (支持封禁功能)                    |
| subscription            | ENUM      | `free`, `premium`, `enterprise` (会员等级) |
| subscription_expires_at | TIMESTAMP | 会员到期时间                               |

#### B. `books` (词书表 - 来源管理)

| **字段**      | **类型**  | **说明**                                        |
| ------------- | --------- | ----------------------------------------------- |
| id            | INT       | PK                                              |
| title         | VARCHAR   | 书名 (e.g., "2024考研英语红宝书")               |
| description   | TEXT      | 词书描述                                        |
| file_url      | VARCHAR   | PDF文件存储地址                                 |
| file_size     | BIGINT    | 文件大小 (字节)                                 |
| total_pages   | INT       | 总页数                                          |
| total_words   | INT       | 总单词数                                        |
| status        | ENUM      | `processing` (解析中), `ready` (就绪), `failed` |
| error_message | TEXT      | 失败原因 (status=failed时)                      |
| created_by    | INT       | FK -> users.id (上传者)                         |
| created_at    | TIMESTAMP | 创建时间                                        |
| updated_at    | TIMESTAMP | 更新时间                                        |

#### C. `words` (公共单词全库 - 核心资产)

这是所有用户共享的数据。

| **字段**        | **类型**  | **详细说明**                                                 |
| --------------- | --------- | ------------------------------------------------------------ |
| id              | INT       | PK                                                           |
| book_id         | INT       | FK -> books.id                                               |
| spelling        | VARCHAR   | 单词拼写 (唯一索引)                                          |
| phonetic        | VARCHAR   | 音标                                                         |
| definitions     | JSONB     | 核心设计。存储释义，支持多词性。结构见下文。                 |
| sentences       | JSONB     | 扩展设计。存储双语例句。                                     |
| mnemonic        | TEXT      | 扩展设计。记忆技巧/助记口诀。                                |
| difficulty      | INT       | 难度系数 (1-5)                                               |
| frequency_rank  | INT       | 词频排名 (用于优先级排序)                                    |
| tags            | JSONB     | 标签 (e.g., ["cet4", "business", "medical"])                |
| audio_url       | VARCHAR   | 发音音频文件地址 (可选)                                      |
| image_url       | VARCHAR   | 配图地址 (可选，用于图像记忆法)                              |
| created_at      | TIMESTAMP | 创建时间                                                     |
| updated_at      | TIMESTAMP | 更新时间                                                     |
| ai_generated    | BOOLEAN   | 标记是否为AI生成内容 (用于质量追踪)                          |
| quality_score   | FLOAT     | 内容质量评分 (0-1，基于用户反馈)                             |

> **JSONB 数据结构示例 (definitions & sentences):**
>
> JSON
>
> ```
> // definitions
> [
>   {"pos": "vt", "cn": "装饰; 点缀", "en": "make something look more attractive"},
>   {"pos": "n", "cn": "勋章 (少见用法)", "en": "medal"}
> ]
> ```

> // sentences
>
> [
>
> {"en": "They decorated the room with flowers.", "cn": "他们用花装饰了房间。"},
>
> {"en": "He was decorated for bravery.", "cn": "他因英勇而被授勋。"}
>
> ]

#### D. `user_progress` (用户学习轨迹 - 数据隔离)

| **字段**           | **类型**  | **说明**                                                     |
| ------------------ | --------- | ------------------------------------------------------------ |
| id                 | BIGINT    | PK                                                           |
| user_id            | INT       | FK -> users.id (隔离键)                                      |
| word_id            | INT       | FK -> words.id                                               |
| **status**         | INT       | 0:未学, 1:学习中, 2:复习中, 3:已掌握                         |
| **next_review_at** | TIMESTAMP | 下次复习时间 (算法计算)                                      |
| **ease_factor**    | FLOAT     | SM-2算法因子 (默认2.5)                                       |
| **interval**       | INT       | 当前复习间隔 (天)                                            |
| **repetitions**    | INT       | 连续正确次数                                                 |
| **last_review_at** | TIMESTAMP | 上次复习时间                                                 |
| **total_reviews**  | INT       | 总复习次数                                                   |
| **correct_count**  | INT       | 正确次数                                                     |
| **history**        | JSONB     | 每次复习的记录日志 (用于生成学习曲线图表)                    |
| created_at         | TIMESTAMP | 首次学习时间                                                 |
| updated_at         | TIMESTAMP | 最后更新时间                                                 |

**索引设计**：
- 复合索引：`(user_id, next_review_at)` - 用于快速查询待复习单词
- 复合索引：`(user_id, status)` - 用于统计学习进度
- 唯一索引：`(user_id, word_id)` - 防止重复记录

#### E. `user_study_plans` (学习计划表 - 新增)

| **字段**       | **类型**  | **说明**                                      |
| -------------- | --------- | --------------------------------------------- |
| id             | INT       | PK                                            |
| user_id        | INT       | FK -> users.id                                |
| book_id        | INT       | FK -> books.id                                |
| name           | VARCHAR   | 计划名称 (e.g., "考研英语30天冲刺")           |
| daily_new      | INT       | 每日新词数量                                  |
| daily_review   | INT       | 每日复习数量上限                              |
| start_date     | DATE      | 开始日期                                      |
| target_date    | DATE      | 目标完成日期                                  |
| is_active      | BOOLEAN   | 是否激活                                      |
| created_at     | TIMESTAMP | 创建时间                                      |
| updated_at     | TIMESTAMP | 更新时间                                      |

#### F. `user_feedback` (用户反馈表 - 质量改进)

| **字段**      | **类型**  | **说明**                                   |
| ------------- | --------- | ------------------------------------------ |
| id            | BIGINT    | PK                                         |
| user_id       | INT       | FK -> users.id                             |
| word_id       | INT       | FK -> words.id                             |
| feedback_type | ENUM      | `helpful`, `incorrect`, `inappropriate`    |
| content_type  | ENUM      | `definition`, `sentence`, `mnemonic`       |
| comment       | TEXT      | 具体反馈内容                               |
| created_at    | TIMESTAMP | 反馈时间                                   |

#### G. `celery_tasks` (任务追踪表)

| **字段**       | **类型**  | **说明**                                        |
| -------------- | --------- | ----------------------------------------------- |
| id             | BIGINT    | PK                                              |
| task_id        | VARCHAR   | Celery任务ID (唯一索引)                         |
| task_type      | ENUM      | `pdf_parse`, `ai_enrich`, `audio_generate`      |
| status         | ENUM      | `pending`, `running`, `completed`, `failed`     |
| progress       | INT       | 进度百分比 (0-100)                              |
| result         | JSONB     | 任务结果数据                                    |
| error_message  | TEXT      | 错误信息                                        |
| created_by     | INT       | FK -> users.id                                  |
| created_at     | TIMESTAMP | 创建时间                                        |
| started_at     | TIMESTAMP | 开始时间                                        |
| completed_at   | TIMESTAMP | 完成时间                                        |

------

## 三、 核心功能模块详细设计

### 模块 1：智能导入与增强管道 (The Smart ETL Pipeline)

这是本系统的“黑科技”部分，解决“PDF到富文本数据库”的问题。

**流程步骤：**

1. **上传与切片：** 管理员上传PDF，后台通过 `pdf2image` 将每一页转为高清图片。

2. **OCR 识别：** 调用 `PaddleOCR` 识别图片中的文本块，保留坐标信息。

3. **结构化清洗 (LLM Agent)：**

   - OCR出来的结果通常是散乱的（例如音标可能识别成乱码）。
   - **策略：** 将OCR识别出的原始文本块发送给 LLM (如 GPT-3.5/4o-mini 或 DeepSeek)，Prompt 如下：

   > "我有一段OCR识别的混乱文本，请帮我提取其中的单词信息。输出为标准JSON格式，包含 word, phonetic, definition。如果文本中有噪音请忽略。"

4. **AI 增强 (Enrichment)：**

   - 如果PDF中**没有**例句或记忆法（大多数单词书只有定义），触发**增强任务**。
   - **Prompt:** "请为单词 'decorate' 生成 2 个适合大学六级水平的英汉双语例句，并提供一个巧妙的记忆法（词根词缀法或联想记忆法）。"

5. **入库：** 将清洗后的基础数据 + AI生成的增强数据存入 `words` 表。

### 模块 2：记忆算法引擎 (Review Engine)

不使用简单的随机算法，而是实现 **SuperMemo-2 (SM-2)** 算法。

- **用户交互：** 用户看到单词，选择反馈：

  - `Again` (完全不认识) -> 评分 0
  - `Hard` (模糊) -> 评分 3
  - `Good` (认识但稍慢) -> 评分 4
  - `Easy` (秒杀) -> 评分 5

- **后端计算逻辑 (Python伪代码)：**

  Python

  ```
  def calculate_next_review(quality, prev_interval, prev_ease_factor):
      if quality < 3:
          # 没记住，重置进度
          return 1, prev_ease_factor # 1天后复习
  
      # 计算新的难度因子
      new_ef = prev_ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
      new_ef = max(1.3, new_ef) # 设下限
  
      # 计算新的间隔
      if prev_interval == 0:
          new_interval = 1
      elif prev_interval == 1:
          new_interval = 6
      else:
          new_interval = int(prev_interval * new_ef)
  
      return new_interval, new_ef
  ```

------

## 四、 API 接口设计 (RESTful示例)

为了方便前端开发，我们需要定义清晰的接口。

### 1. 认证模块 (Authentication)

#### 用户注册/登录
- `POST /api/auth/register`
  - **请求体**：`{ "username": "user1", "email": "user@example.com", "password": "xxx" }`
  - **返回**：`{ "user_id": 1, "token": "jwt_token" }`

- `POST /api/auth/login`
  - **请求体**：`{ "email": "user@example.com", "password": "xxx" }`
  - **返回**：`{ "user_id": 1, "token": "jwt_token", "expires_at": "2024-12-31T23:59:59Z" }`

- `POST /api/auth/refresh`
  - **请求头**：`Authorization: Bearer {refresh_token}`
  - **返回**：新的访问令牌

- `POST /api/auth/logout`
  - **功能**：使当前token失效（加入黑名单）

### 2. 学习区 (Study)

#### 获取学习任务
- `GET /api/study/session`
  - **查询参数**：`?limit=20&include_new=true`
  - **功能**：获取今日待复习 + 今日新学的单词列表
  - **逻辑**：
    1. 查询 `user_progress` 中 `next_review_at <= now()` 的记录
    2. 如果不足，从用户激活的学习计划中补足新词
    3. 按优先级排序：过期时间越久优先级越高
  - **返回**：
    ```json
    {
      "session_id": "uuid",
      "words": [
        {
          "word_id": 101,
          "spelling": "decorate",
          "phonetic": "/ˈdekəreɪt/",
          "definitions": [...],
          "sentences": [...],
          "mnemonic": "...",
          "audio_url": "https://...",
          "progress": {
            "status": 2,
            "ease_factor": 2.5,
            "interval": 3
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

#### 提交学习结果
- `POST /api/study/submit`
  - **请求体**：
    ```json
    {
      "session_id": "uuid",
      "word_id": 101,
      "quality": 4,
      "time_spent": 5.2
    }
    ```
  - **逻辑**：
    1. 运行SM-2算法计算新的 `next_review_at`
    2. 更新 `user_progress` 表
    3. 记录到 `history` JSONB字段
  - **返回**：
    ```json
    {
      "next_review_at": "2024-12-15T10:00:00Z",
      "interval": 6,
      "ease_factor": 2.6,
      "status": 2
    }
    ```

#### 学习统计
- `GET /api/study/stats`
  - **查询参数**：`?period=week` (day/week/month/all)
  - **返回**：
    ```json
    {
      "total_words": 500,
      "mastered": 120,
      "learning": 280,
      "new": 100,
      "daily_streak": 15,
      "accuracy_rate": 0.85,
      "time_spent_minutes": 450,
      "chart_data": {
        "dates": ["2024-12-01", "2024-12-02", ...],
        "reviews": [20, 25, 18, ...],
        "accuracy": [0.8, 0.85, 0.9, ...]
      }
    }
    ```

#### 学习计划管理
- `POST /api/study/plans`
  - **请求体**：
    ```json
    {
      "book_id": 1,
      "name": "考研英语30天冲刺",
      "daily_new": 50,
      "daily_review": 100,
      "start_date": "2024-12-01",
      "target_date": "2024-12-31"
    }
    ```

- `GET /api/study/plans`
  - **返回**：用户所有学习计划列表

- `PUT /api/study/plans/{plan_id}`
  - **功能**：更新学习计划

- `DELETE /api/study/plans/{plan_id}`
  - **功能**：删除学习计划

### 3. 词书管理 (Books)

- `GET /api/books`
  - **查询参数**：`?page=1&limit=20&status=ready`
  - **返回**：可用词书列表

- `GET /api/books/{book_id}`
  - **返回**：词书详情及单词预览

- `GET /api/books/{book_id}/words`
  - **查询参数**：`?page=1&limit=50&search=dec`
  - **返回**：词书中的单词列表（支持搜索）

### 4. 用户反馈 (Feedback)

- `POST /api/feedback`
  - **请求体**：
    ```json
    {
      "word_id": 101,
      "feedback_type": "incorrect",
      "content_type": "definition",
      "comment": "第二个释义有误"
    }
    ```
  - **功能**：收集用户反馈，用于改进内容质量

### 5. 管理区 (Admin)

#### PDF上传与解析
- `POST /api/admin/books/upload`
  - **请求体**：`multipart/form-data`
  - **字段**：
    - `file`: PDF文件
    - `title`: 词书名称
    - `description`: 描述
  - **返回**：
    ```json
    {
      "book_id": 1,
      "task_id": "celery-task-uuid",
      "status": "processing"
    }
    ```

- `GET /api/admin/tasks/{task_id}`
  - **返回**：
    ```json
    {
      "task_id": "uuid",
      "task_type": "pdf_parse",
      "status": "running",
      "progress": 45,
      "message": "正在处理第 23/50 页",
      "created_at": "2024-12-09T10:00:00Z",
      "started_at": "2024-12-09T10:00:05Z"
    }
    ```

- `POST /api/admin/tasks/{task_id}/cancel`
  - **功能**：取消正在运行的任务

#### 内容管理
- `GET /api/admin/words`
  - **查询参数**：`?page=1&limit=50&ai_generated=true&quality_score_lt=0.5`
  - **返回**：单词列表（支持筛选低质量内容）

- `PUT /api/admin/words/{word_id}`
  - **功能**：手动编辑单词内容

- `DELETE /api/admin/words/{word_id}`
  - **功能**：删除单词

- `POST /api/admin/words/{word_id}/regenerate`
  - **请求体**：`{ "content_type": "sentences" }`
  - **功能**：重新生成AI内容（例句或记忆法）

#### 用户管理
- `GET /api/admin/users`
  - **查询参数**：`?page=1&limit=50&role=user&is_active=true`
  - **返回**：用户列表

- `PUT /api/admin/users/{user_id}`
  - **功能**：更新用户信息（修改角色、会员等级、封禁等）

#### 系统监控
- `GET /api/admin/stats/system`
  - **返回**：
    ```json
    {
      "total_users": 1000,
      "active_users_today": 150,
      "total_words": 50000,
      "total_books": 20,
      "ai_requests_today": 500,
      "storage_used_gb": 2.5,
      "celery_queue_length": 3
    }
    ```

- `GET /api/admin/feedback`
  - **查询参数**：`?feedback_type=incorrect&resolved=false`
  - **返回**：用户反馈列表（用于内容质量改进）

------

## 五、 开发实施步骤指南 (Action Plan)

如果你准备开始动手，建议按照以下阶段进行：

### 第一阶段：最小可行性模型 (MVP) - 验证OCR

1. **任务**：写一个单纯的 Python 脚本。
2. **输入**：你提供的本地图片。
3. **处理**：使用 PaddleOCR 提取文字，用 正则表达式 或 OpenAI API 提取 JSON。
4. **输出**：打印在控制台。
   - *目的：确认我们能搞定那个扫描件的数据质量。*

### 第二阶段：后端与数据库基础

1. 搭建 FastAPI 项目骨架。
2. 使用 Docker 部署 PostgreSQL。
3. 编写 `models.py` 定义 Word 和 User 表。
4. 实现注册/登录接口 (JWT)。

### 第三阶段：核心业务串联

1. 实现“上传PDF -> 异步入库”流程。
2. 实现“获取单词 -> 提交打分”流程。

### 第四阶段：前端与可视化

1. 搭建 Vue3 页面。
2. 制作漂亮的"单词卡片"组件（点击翻转，显示例句和记忆法）。
3. 实现学习统计图表和进度可视化。

------

## 六、 技术实现细节与最佳实践

### 1. 性能优化策略

#### 数据库优化
- **连接池配置**：使用 SQLAlchemy 异步连接池，设置合理的 `pool_size` 和 `max_overflow`
- **查询优化**：
  - 使用 `select_in_loading` 避免 N+1 查询问题
  - 对高频查询字段建立索引
  - 使用 PostgreSQL 的 `EXPLAIN ANALYZE` 分析慢查询
- **分页策略**：使用游标分页而非 offset/limit（大数据量时性能更好）

#### Redis 缓存策略
```python
# 缓存层次设计
1. 热点单词数据：TTL 1小时
   Key: "word:{word_id}"

2. 用户学习会话：TTL 30分钟
   Key: "session:{user_id}:{session_id}"

3. 每日统计数据：TTL 24小时
   Key: "stats:daily:{user_id}:{date}"

4. API 限流：滑动窗口算法
   Key: "ratelimit:{user_id}:{endpoint}"
```

#### Celery 任务优化
- **任务优先级**：使用 Celery 的优先级队列
  - 高优先级：用户触发的 AI 增强请求
  - 中优先级：PDF 解析任务
  - 低优先级：批量数据清洗
- **任务重试策略**：
  ```python
  @celery_app.task(
      bind=True,
      max_retries=3,
      default_retry_delay=60,
      autoretry_for=(NetworkError, APIError)
  )
  def enrich_word_with_ai(self, word_id):
      # 实现逻辑
      pass
  ```

### 2. 安全性设计

#### 认证与授权
- **JWT Token 设计**：
  - Access Token：15分钟过期
  - Refresh Token：7天过期，存储在 Redis 中
  - Token 黑名单机制（用户登出时）
- **密码策略**：
  - 使用 bcrypt 哈希（cost factor = 12）
  - 强制密码复杂度要求
  - 登录失败次数限制（5次/15分钟）

#### API 安全
- **速率限制**：
  - 普通用户：100 请求/分钟
  - Premium 用户：500 请求/分钟
  - Admin：无限制
- **输入验证**：使用 Pydantic 模型严格验证所有输入
- **SQL 注入防护**：使用 SQLAlchemy ORM，避免原生 SQL
- **XSS 防护**：前端使用 Vue 的自动转义，后端对用户输入进行清洗

#### 文件上传安全
```python
# PDF 上传验证
ALLOWED_EXTENSIONS = {'.pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def validate_pdf_upload(file):
    # 1. 检查文件扩展名
    # 2. 检查 MIME 类型
    # 3. 检查文件大小
    # 4. 使用 PyPDF2 验证 PDF 结构
    # 5. 病毒扫描（可选，使用 ClamAV）
```

### 3. AI 集成最佳实践

#### Prompt Engineering 模板

**数据清洗 Prompt**：
```python
CLEANING_PROMPT = """
你是一个专业的词汇数据清洗助手。我有一段OCR识别的文本，请提取其中的单词信息。

OCR文本：
{ocr_text}

要求：
1. 提取单词拼写（spelling）
2. 提取音标（phonetic），如果音标有乱码请尝试修复
3. 提取所有释义（definitions），包含词性和中英文解释
4. 忽略页码、页眉等噪音
5. 输出严格的JSON格式

输出格式：
{{
  "spelling": "word",
  "phonetic": "/wɜːrd/",
  "definitions": [
    {{"pos": "n", "cn": "单词", "en": "a unit of language"}}
  ]
}}
"""

ENRICHMENT_PROMPT = """
你是一个英语教学专家。请为单词 "{word}" 生成学习材料。

当前信息：
- 拼写：{spelling}
- 音标：{phonetic}
- 释义：{definitions}

请生成：
1. 2-3个双语例句（适合{level}水平）
   - 例句要实用、地道
   - 覆盖不同词性和用法

2. 一个记忆技巧
   - 优先使用词根词缀法
   - 如无词根，使用联想记忆法
   - 简洁易记

输出JSON格式：
{{
  "sentences": [
    {{"en": "...", "cn": "..."}}
  ],
  "mnemonic": "..."
}}
"""
```

#### API 调用优化
- **批量处理**：将多个单词的增强请求合并为一个 API 调用
- **错误处理**：
  ```python
  async def call_llm_with_retry(prompt, max_retries=3):
      for attempt in range(max_retries):
          try:
              response = await openai_client.chat.completions.create(
                  model="gpt-3.5-turbo",
                  messages=[{"role": "user", "content": prompt}],
                  temperature=0.7,
                  max_tokens=500
              )
              return response
          except RateLimitError:
              await asyncio.sleep(2 ** attempt)  # 指数退避
          except APIError as e:
              logger.error(f"API error: {e}")
              if attempt == max_retries - 1:
                  raise
  ```
- **成本控制**：
  - 使用 token 计数器预估成本
  - 设置每日 API 调用上限
  - 优先使用缓存的结果

### 4. 监控与日志

#### 日志策略
```python
# 结构化日志
import structlog

logger = structlog.get_logger()

# 关键操作日志
logger.info(
    "user_study_session",
    user_id=user_id,
    session_id=session_id,
    words_count=len(words),
    duration_seconds=duration
)

# 错误日志
logger.error(
    "pdf_parse_failed",
    book_id=book_id,
    error=str(e),
    traceback=traceback.format_exc()
)
```

#### 性能监控
- **APM 工具**：集成 Sentry 或 New Relic
- **关键指标**：
  - API 响应时间（P50, P95, P99）
  - 数据库查询时间
  - Celery 任务队列长度
  - Redis 命中率
  - AI API 调用成功率和延迟

#### 业务指标监控
```python
# 使用 Prometheus + Grafana
from prometheus_client import Counter, Histogram

# 用户学习指标
study_sessions_total = Counter('study_sessions_total', 'Total study sessions')
words_reviewed_total = Counter('words_reviewed_total', 'Total words reviewed')
review_accuracy = Histogram('review_accuracy', 'Review accuracy distribution')

# AI 生成指标
ai_enrichment_duration = Histogram('ai_enrichment_duration_seconds', 'AI enrichment duration')
ai_quality_score = Histogram('ai_quality_score', 'AI generated content quality')
```

### 5. 数据备份与灾难恢复

#### 备份策略
- **数据库备份**：
  - 全量备份：每日凌晨 2:00
  - 增量备份：每 6 小时
  - 保留策略：最近 7 天全量 + 30 天增量
- **文件存储备份**：
  - PDF 文件：使用 S3 的版本控制
  - 音频文件：跨区域复制

#### 灾难恢复计划
1. **RTO (Recovery Time Objective)**：4 小时
2. **RPO (Recovery Point Objective)**：1 小时
3. **恢复流程**：
   - 从最近的备份恢复数据库
   - 重放 WAL 日志到故障点
   - 验证数据完整性
   - 切换 DNS 到备用服务器

------

## 七、 部署架构

### 1. Docker Compose 开发环境

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: smart_vocab
      POSTGRES_USER: vocab_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes

  minio:
    image: minio/minio
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://vocab_user:${DB_PASSWORD}@postgres/smart_vocab
      REDIS_URL: redis://redis:6379/0
      MINIO_ENDPOINT: minio:9000
    depends_on:
      - postgres
      - redis
      - minio
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app

  celery_worker:
    build: ./backend
    command: celery -A app.tasks worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://vocab_user:${DB_PASSWORD}@postgres/smart_vocab
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  celery_beat:
    build: ./backend
    command: celery -A app.tasks beat --loglevel=info
    environment:
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
    environment:
      VITE_API_URL: http://localhost:8000

volumes:
  postgres_data:
  minio_data:
```

### 2. 生产环境部署（Kubernetes）

**关键配置**：
- **水平扩展**：
  - Backend API：3-5 个 Pod（根据负载自动扩展）
  - Celery Worker：5-10 个 Pod
- **资源限制**：
  ```yaml
  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"
    limits:
      memory: "1Gi"
      cpu: "1000m"
  ```
- **健康检查**：
  ```yaml
  livenessProbe:
    httpGet:
      path: /health
      port: 8000
    initialDelaySeconds: 30
    periodSeconds: 10
  ```

### 3. CI/CD 流程

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/ --cov=app

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker image
        run: docker build -t smart-vocab:${{ github.sha }} .
      - name: Push to registry
        run: docker push smart-vocab:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: kubectl set image deployment/backend backend=smart-vocab:${{ github.sha }}
```

------

## 八、 成本估算与商业化

### 1. 基础设施成本（月度）

| **项目**         | **配置**                  | **成本（USD）** |
| ---------------- | ------------------------- | --------------- |
| 云服务器         | 4核8G × 3                 | $150            |
| PostgreSQL RDS   | 2核4G + 100GB SSD         | $80             |
| Redis            | 2GB 内存                  | $30             |
| 对象存储         | 500GB + 流量              | $25             |
| CDN              | 1TB 流量                  | $50             |
| **小计**         |                           | **$335**        |

### 2. AI API 成本估算

假设每个单词生成成本：
- 数据清洗：~500 tokens × $0.0005/1K = $0.00025
- 内容增强：~800 tokens × $0.0005/1K = $0.0004
- **单词总成本**：~$0.00065

如果处理 10,000 个单词：$6.5

### 3. 定价策略建议

| **套餐**     | **价格**    | **功能**                                   |
| ------------ | ----------- | ------------------------------------------ |
| 免费版       | $0/月       | 500词上限，基础功能                        |
| 标准版       | $9.9/月     | 无词数限制，AI增强内容，学习统计           |
| 专业版       | $19.9/月    | 所有功能 + 自定义词书上传 + 优先AI生成     |
| 企业版       | $99/月起    | 团队管理，API访问，专属服务器              |

------

## 九、 风险与挑战

### 1. 技术风险

| **风险**             | **影响** | **缓解措施**                                   |
| -------------------- | -------- | ---------------------------------------------- |
| OCR 识别准确率低     | 高       | 人工审核机制 + 用户反馈系统 + 多OCR引擎对比   |
| AI 生成内容质量不稳定 | 中       | 质量评分系统 + 人工抽检 + Prompt 持续优化      |
| 数据库性能瓶颈       | 中       | 读写分离 + 分库分表 + 缓存优化                 |
| 并发量突增           | 中       | 自动扩展 + 限流 + CDN                          |

### 2. 业务风险

| **风险**         | **影响** | **缓解措施**                       |
| ---------------- | -------- | ---------------------------------- |
| 版权问题         | 高       | 仅处理公版或授权内容               |
| 用户留存率低     | 高       | 游戏化设计 + 社交功能 + 每日提醒   |
| 竞品压力         | 中       | 差异化功能（AI增强）+ 用户体验优化 |

------

## 十、 未来扩展方向

### 1. 短期（3-6个月）
- [ ] 移动端 App（React Native）
- [ ] 语音识别练习功能
- [ ] 社区功能（学习小组、排行榜）
- [ ] 更多词书来源（支持 Excel、Word 导入）

### 2. 中期（6-12个月）
- [ ] 多语言支持（日语、韩语、法语等）
- [ ] AI 对话练习（基于 GPT-4）
- [ ] 个性化学习路径推荐
- [ ] 企业版团队管理功能

### 3. 长期（12个月+）
- [ ] 扩展到其他学科（医学术语、法律词汇等）
- [ ] VR/AR 沉浸式学习
- [ ] 开放 API 平台
- [ ] 国际化运营