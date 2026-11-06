# QA 测试工作台 · 装修共享网站

> 企业级「开发期间同步测试」落地：测试左移 + 分层自动化 + 质量门禁。
> 唯一真实来源：`tests/`（可执行用例，AAA 三要素）；`defects.csv` 只记缺陷状态。

## 测试对象

| 层 | 工具 | 目录 | 状态 |
|---|---|---|---|
| 后端接口/单测 | pytest + httpx | `backend/tests/` | ✅ 已搭建 |
| 前端单测 | Vitest + @vue/test-utils | `frontend/` | ⏳ 待搭建 |
| E2E | Playwright | （后续） | ⏳ 待搭建 |

## 质量门禁（铁闸，全绿才放行）

| 指标 | 目标 |
|---|---|
| 用例执行率 | 100% |
| 通过率 | ≥ 80% |
| P0 缺陷 | 归零（24h 内修复） |
| 安全覆盖 | ≥ 90%（RBAC 越权、路径穿越、密码哈希） |

## 缺陷分级

- **P0** 阻断：数据丢失 / 越权 / 崩溃，24 小时内修复
- **P1** 严重：核心流程不可用，本迭代必修
- **P2** 一般：功能可用但有明显缺陷
- **P3** 轻微：体验/文案问题
- **P4** 建议：有空再改

## 目录结构

```
qa/
├─ README.md            # 本说明
├─ defects.csv          # 缺陷追踪表（状态唯一入口）
└─ MASTER_PROMPT.md     # LLM 自主执行主提示词
backend/tests/          # pytest 用例（AAA）
```

## 执行方式

```bash
# 后端
cd backend
pip install -r requirements-dev.txt
python -m pytest -v

# 前端
cd frontend
npm install
npm run test
```

## 角色与账号（测试种子）

| 角色 | 账号 | 密码 |
|---|---|---|
| 超级管理员 | 001 | WENjing970217 |
| 内容管理员 | 002 | WENjing521 |
| 普通用户 | qa_user（测试内创建） | qa_user@123 |
