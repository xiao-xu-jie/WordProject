# Smart Vocab 前端

基于 Vue 3 + TypeScript + Naive UI 的智能词汇学习平台前端应用。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript 超集
- **Vite** - 下一代前端构建工具
- **Naive UI** - Vue 3 组件库
- **Vue Router** - 官方路由管理器
- **Pinia** - Vue 3 状态管理
- **Axios** - HTTP 客户端

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口层
│   │   ├── axios.ts      # Axios 配置和拦截器
│   │   ├── auth.ts       # 认证相关 API
│   │   ├── study.ts      # 学习相关 API
│   │   └── admin.ts      # 管理员相关 API
│   ├── components/       # 可复用组件
│   │   └── WordCard.vue  # 单词卡片组件（翻转动画）
│   ├── views/            # 页面组件
│   │   ├── Login.vue     # 登录页面
│   │   ├── Register.vue  # 注册页面
│   │   ├── Study.vue     # 学习会话页面
│   │   └── Admin.vue     # 管理后台页面
│   ├── stores/           # Pinia 状态管理
│   │   ├── auth.ts       # 用户认证状态
│   │   └── study.ts      # 学习会话状态
│   ├── router/           # 路由配置
│   │   └── index.ts      # 路由定义和守卫
│   ├── types/            # TypeScript 类型定义
│   │   └── index.ts      # 全局类型定义
│   ├── App.vue           # 根组件
│   └── main.ts           # 应用入口
├── index.html            # HTML 模板
├── vite.config.ts        # Vite 配置
├── tsconfig.json         # TypeScript 配置
└── package.json          # 项目依赖
```

## 功能特性

### 用户功能
- ✅ 用户注册和登录（JWT 认证）
- ✅ 学习会话管理（获取今日复习词 + 新词）
- ✅ 单词卡片翻转动画（点击查看详情）
- ✅ SM-2 算法评分系统（0/3/4/5 四档评分）
- ✅ 学习进度追踪

### 管理员功能
- ✅ PDF 文档上传
- ✅ 异步任务进度监控（轮询）
- ✅ 书籍列表管理
- ✅ 书籍删除功能

### 技术亮点
- 🎨 响应式设计，支持移动端
- 🔐 JWT Token 自动刷新和拦截
- 🎯 路由守卫（认证和权限控制）
- 📊 实时任务进度显示
- 🎴 3D 翻转卡片动画
- 🌈 渐变色主题设计

## 开发指南

### 安装依赖

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 类型检查

```bash
npm run type-check
```

## API 代理配置

开发环境下，Vite 会将 `/api` 请求代理到后端服务器（默认 `http://localhost:8000`）。

如需修改后端地址，请编辑 `vite.config.ts`：

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://your-backend-url:8000',
      changeOrigin: true
    }
  }
}
```

## 环境要求

- Node.js >= 16
- npm >= 8

## 页面说明

### 登录页面 (`/login`)
- 用户名和密码登录
- 表单验证
- 自动跳转到学习页面

### 注册页面 (`/register`)
- 邮箱、用户名、密码注册
- 密码确认验证
- 注册成功后自动登录

### 学习页面 (`/study`)
- 显示今日学习任务（复习词 + 新词）
- 单词卡片翻转查看详情
- 四档评分按钮（忘记了/模糊/想起来了/很容易）
- 学习进度条
- 完成提示

### 管理后台 (`/admin`)
- 仅管理员可访问
- PDF 文件上传
- 实时显示处理进度
- 书籍列表展示
- 书籍删除功能

## 状态管理

### Auth Store
- `token`: JWT Token
- `user`: 当前用户信息
- `isAuthenticated`: 是否已登录
- `isAdmin`: 是否为管理员
- `login()`: 登录
- `register()`: 注册
- `logout()`: 退出登录

### Study Store
- `session`: 当前学习会话
- `currentWord`: 当前单词
- `currentIndex`: 当前索引
- `loadSession()`: 加载学习会话
- `submitReview()`: 提交评分
- `reset()`: 重置状态

## 常见问题

### 1. 登录后无法访问页面
检查后端服务是否正常运行，以及 API 代理配置是否正确。

### 2. 上传 PDF 后没有反应
确保后端 Celery Worker 正在运行，用于处理异步任务。

### 3. 样式显示异常
清除浏览器缓存，或尝试重新安装依赖：
```bash
rm -rf node_modules package-lock.json
npm install
```

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT
