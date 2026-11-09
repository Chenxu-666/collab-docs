# 装修共享网站（企业级落地版 v2.0）

基于 Vue3 + FastAPI 的装修资料共享网站。文档、参考图片、避坑经验三类内容集中共享，游客只读、注册审批、管理员协同维护，操作全程留痕、响应式多端。

## 功能

- 🔐 四级权限：超级管理员 / 内容管理员 / 普通用户（审批后只读）/ 游客
- 📝 自助注册：公开注册 → 待审批 → 超级管理员通过/拒绝
- 📄 文档管理：上传（docx/pdf）、在线协同编辑（OnlyOffice，可选）、版本回滚、下载（仅管理员）
- 🖼️ 图片库：相册分类、等比网格、灯箱大图、批量上传
- ⚠️ 避坑项：阶段/分类/风险等级、置顶、关联图片与文档、逐条维护
- 🚀 发布工作流：草稿 / 已发布 / 已归档，撤回即时生效
- 🗑 回收站：软删除 + 恢复 + 超管彻底删除
- 📊 统计看板：内容数量、发布趋势（日/周聚合）
- 📋 操作审计：全量留痕、不可删除、可筛选
- 📱 响应式：PC + 手机端（用户端 / 管理端双路由）

## 目录结构

```
collab-docs/
├─ backend/          FastAPI 后端（app/api/v1 分模块）
├─ frontend/         Vue3 前端（用户端 + /admin 管理端）
├─ docker-compose.yml
└─ README.md
```

## 快速启动（本地开发）

### 1. 启动后端

```bash
cd backend
pip install -r requirements.txt
python run.py
# 后端运行于 http://localhost:8000，首次启动自动建表并写入种子数据
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
# 前端运行于 http://localhost:5173（已代理 /api 到 8000）
```

### 3. 登录

| 角色 | 账号 | 密码 |
|------|------|------|
| 超级管理员 | 001 | WENjing970217 |
| 内容管理员 | 002 | WENjing521 |

- 游客无需登录即可浏览公开首页、文档、图片库、避坑清单。
- 新用户可点击「注册」提交申请，由超级管理员（001）在管理端「账号管理-待审批」中通过后方可登录。

## 用户端 / 管理端

- 用户端：`http://localhost:5173/`（公开只读，展示已发布内容）
- 管理端：`http://localhost:5173/admin`（登录后进入，需管理员/超管）
- 超级管理员额外拥有「账号管理」（注册审批、建号、停用）与「彻底删除」权限。

## 启用 OnlyOffice 协同编辑

1. `docker compose up -d onlyoffice`
2. 在后端 `.env` 配置 `ONLYOFFICE_URL=http://localhost:8888`、`APP_BASE_URL=http://localhost:8000`，并设置长度不少于 32 字符的 `ONLYOFFICE_SECRET`（回调需 JWT 校验）
3. 未配置时，编辑页自动降级为提示 + 下载。

## Docker 全量部署

```bash
docker compose up -d
# 前端构建产物放入 Nginx 或使用静态托管，反向代理 /api 到 app:8000
```

## 数据库

- 默认 SQLite（`backend/collab_docs.db`），零依赖可直接跑通
- 生产环境切换 MySQL：设置 `DATABASE_URL=mysql+pymysql://user:pass@host:3306/collab_docs`

## Railway + Vercel 部署

### 后端（Railway）

- 服务根目录设置为 `backend`，使用其中的 `Dockerfile` 构建；启动命令会读取 Railway 注入的 `PORT`。
- 配置 `DATABASE_URL`、`ENV=prod`、长度不少于 32 字符的随机 `JWT_SECRET`、`FILE_ROOT=/app/data/files` 与 `CORS_ORIGINS`。
- `CORS_ORIGINS` 填写 Vercel 正式域名，多个域名用英文逗号分隔，不要填写路径或末尾斜杠。
- 健康检查路径为 `/api/health`；上传文件目录必须挂载持久化 Volume。

### 前端（Vercel）

- 项目根目录设置为 `frontend`，构建命令为 `npm run build`，输出目录为 `dist`。
- 配置 `VITE_API_BASE_URL=https://你的后端域名.up.railway.app`，只填后端域名，不要在末尾添加 `/api/v1`。
- 本地开发不设置该变量，前端会继续通过 Vite 代理访问 `http://localhost:8000`。

## 技术栈

前端 Vite + Vue3 + TS + Pinia + Vue Router ｜ 后端 FastAPI + SQLAlchemy 2.0 + PyJWT ｜ 文档服务 OnlyOffice（可选）｜ 存储本地盘（预留 MinIO）

> 本系统为产品设计落地实现，具体使用请结合公司合规与安全要求。
