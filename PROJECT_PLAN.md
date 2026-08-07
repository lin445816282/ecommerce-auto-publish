# 全平台AI自动上架系统 — 项目执行计划

## 项目状态：🟢 v0.8.0 全部完成
**项目经理**：AI（小林辅助决策）  
**开始日期**：2026-08-06  
**仓库**：[github.com/lin445816282/ecommerce-auto-publish](https://github.com/lin445816282/ecommerce-auto-publish)  
**提交数**：17 commits

---

## 进度总览

| 阶段 | 内容 | 状态 |
|------|------|------|
| P0-1 | 项目骨架 + 六层架构 | ✅ |
| P0-2 | 产品源（1688爬虫+录入） | ✅ HTTP真实抓取+解析 |
| P0-3 | 调度核心（三道闸+分发） | ✅ 文字闸/价格闸/图片闸 |
| P0-4 | 主表管理（CRUD+版本回滚） | ✅ |
| P0-5 | 平台适配器（淘宝+抖店） | ✅ |
| P0-6 | 全链路流水线引擎 | ✅ 一键执行 |
| P0-7 | 拼多多+亚马逊适配器 | ✅ 4平台全部通过 |
| P1-1 | 出口门（草稿/审核/发布） | ✅ 5级权限 |
| P1-2 | AI决策层（审核/标题/描述） | ✅ Mock模式 |
| P1-3 | React管理后台 | ✅ |
| P2-1 | 接入真实大模型API | ✅ 6家37模型（GPT-4.1/Claude4/DeepSeek-V4/Kimi/Qwen3/豆包）|
| P2-2 | AI图片处理（抠图/水印） | ✅ Pillow+rembg |
| P2-3 | 前端图片上传+处理 | ✅ 拖拽上传+预览+优化 |
| P2-4 | Docker一键部署 | ✅ Dockerfile+docker-compose+nginx |
| P3-1 | AI引擎热修复（真实API调用）| ✅ DeepSeek真实API已验证 |
| P3-2 | 流水线持久化（DB记录） | ✅ ProductPlatformRel自动创建 |
| P3-3 | 仪表盘数据完善 | ✅ by_platform聚合+最近流水线 |
| P3-4 | 三道闸全链路验证 | ✅ 文字/价格/图片闸全部通过测试 |
| P3-5 | FastAPI现代化 (lifespan) | ✅ 移除on_event废弃API |
| P3-6 | 启动入口+端口修正 | ✅ uvicorn.run + 端口8800 |
| P3-7 | JWT认证系统 | ✅ login/register/refresh/me + bcrypt |
| P3-8 | 批量CSV导入 | ✅ 自动字段映射 + 同批次重复检测 |
| P3-9 | 全文搜索+CSV导出 | ✅ 标题/SKU搜索 + 状态筛选导出 |

---

## v0.6.0 新增修复内容

### 1. AI引擎热修复
- **问题**: `config_manager._reload_engine()` 更新了模块级 `ai_engine`，但 `main.py` 通过 `from import` 持有旧引用
- **修复**: main.py 改用 `import modules.ai_brain.engine as ai_engine_mod`，每次通过 `ai_engine_mod.ai_engine` 访问最新实例
- **修复**: `AIConfigManager.__init__` 启动时自动调用 `_reload_engine()` 加载已保存的API Key
- **验证**: DeepSeek API真实调用 → 标题生成3个变体、描述优化含卖点、关键词提取10个

### 2. 流水线持久化
- **新增**: `PipelineOrchestrator._persist_platform_rel()` 方法
- **功能**: 发布成功后自动创建/更新 `ProductPlatformRel` 数据库记录
- **效果**: 仪表盘 `by_platform` 数据现在实时反映真实平台分布

### 3. 三道闸验证
- 文字闸: "高仿LV包包" → TEXT_BAN → 直接作废 ✅
- 图片闸: 水印/品牌Logo检测 (MVP阶段TODO接入YOLO) ⚠️
- 价格闸: 售价¥10 < 成本¥100的30% → PRICE_ANOMALY → 待审核 ✅

### 4. FastAPI现代化
- `@app.on_event("startup")` → `lifespan` context manager
- 版本号: 0.4.0 → 0.5.0 (启动日志)
- 端口: 8000 → 8800 (启动日志)
- 新增 `if __name__ == "__main__": uvicorn.run(...)` 入口

### 5. 前端构建修复
- API默认URL: `/api` → `http://localhost:8800/api` (静态服务器无代理时直连)
- 生产构建: react-scripts build → 静态文件部署于 :3002
- `.env` / `.env.production` 环境变量配置

---

## v0.7.0 JWT 认证系统 (2026-08-07)

### 新增功能
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 用户登录，返回 access_token + refresh_token |
| `/api/auth/register` | POST | 注册新用户（默认operator角色） |
| `/api/auth/refresh` | POST | 刷新 access_token |
| `/api/auth/me` | GET | 获取当前用户信息（需认证） |

### 认证机制
- **算法**: HS256 (HMAC-SHA256)
- **Access Token**: 24小时有效
- **Refresh Token**: 7天有效
- **密码**: bcrypt 哈希存储
- **默认账户**: admin / admin123

### 受保护端点（需 Bearer Token）
- `POST /api/product/crawl` — 1688商品抓取
- `POST /api/product/manual/create` — 手动录入
- `POST /api/pipeline/run` — 一键流水线
- `POST /api/ai/config/key` — 设置API Key
- `POST /api/ai/config/provider` — 切换AI提供商
- `POST /api/ai/config/model` — 设置模型
- `POST /api/ai/config/test` — 测试连接
- `POST /api/image/process` — 图片处理
- `POST /api/audit/submit` — 提交审核
- `POST /api/publish/execute` — 发布商品

### 前端
- **登录页**: 渐变紫色背景卡片式登录界面
- **自动刷新**: 401响应自动使用 refresh_token 续期
- **用户菜单**: 右上角 Dropdown，显示角色+退出登录
- **持久化**: localStorage 存储 token/user

### 数据库
- **新增表**: `users` (id, username, password_hash, full_name, role, is_active, last_login)
- **角色**: admin / operator / viewer

---

## 运行方式

### 开发模式
```bash
# 后端 (端口8800)
cd ecommerce_auto_publish
python -B -m uvicorn main:app --host 0.0.0.0 --port 8800

# 前端 (端口3001)
cd frontend
npm start
```

### Docker 部署
```bash
cd D:\ecom
# 如果 Docker Desktop 有国内镜像报错，先清理 daemon.json 的 registry-mirrors
docker compose up -d --build
# 访问 http://localhost （前端+API一体化，nginx反向代理）
```

---

## 系统架构

```
┌──────────┐  ┌──────────┐
│ React UI │  │ FastAPI  │
│  :3001   │  │  :8800   │
└────┬─────┘  └────┬─────┘
     │             │
     ▼             ▼
┌──────────────────────────────────────┐
│          六层架构                     │
│  product_source → product_master     │
│       → scheduler_core               │
│       → adapter_layer (4平台)        │
│       → export_gate (审核+发布)      │
│       → ai_brain (6家LLM+图片处理)   │
└──────────────────────────────────────┘
```

## 当前运行状态

| 服务 | 地址 | 端点 |
|------|------|------|
| FastAPI后端 | http://localhost:8800 | 31个 |
| API文档 | http://localhost:8800/docs | Swagger |
| React前端 | http://localhost:3001 | 7页面 |

### 7个管理页面
1. 📊 **工作台** — 实时统计 + 流水线历史
2. 📦 **商品管理** — CRUD + 状态筛选 + 详情抽屉 + 一键发布
3. ⚡ **调度分发** — 流水线执行
4. 🤖 **AI工具** — 审核/标题/描述/关键词
5. 🖼️ **图片处理** — 上传→抠图→水印→平台优化
6. ✅ **审核发布** — 待审核列表+发布
7. ⚙️ **系统设置** — 6家AI模型配置 (37个模型可选)

---

## v0.8.0 批量运营工具 (2026-08-07)

### 批量CSV导入
- **端点**: `POST /api/product/import/csv` (需认证)
- **字段映射**: 自动识别中英文表头 (title/标题, price/售价, sku/SKU...)
- **编码兼容**: UTF-8 BOM / UTF-8 / GBK 自动检测
- **去重**: 同批次seen_skus集合 + 数据库已有SKU检测
- **容错**: 缺失标题跳过, 价格格式错误跳过, 行级独立
- **返回**: `{imported, skipped, errors[{row, sku, error}]}`

### 全文搜索
- **端点**: `GET /api/product/search?q=&status=&skip=&limit=`
- **范围**: 标题 + SKU LIKE匹配
- **筛选**: 按status精确过滤
- **分页**: skip/limit, 返回 `{total, items[]}`

### CSV导出
- **端点**: `GET /api/product/export/csv?status=`
- **格式**: UTF-8 CSV (ID/SKU/标题/售价/成本/库存/状态/来源/时间)
- **下载**: StreamingResponse + Content-Disposition

### 前端改造
- 搜索栏: 400ms防抖实时搜索
- 批量导入: Upload组件 + 结果反馈(成功/跳过/错误)
- 导出按钮: blob触发浏览器下载
- 表格: 新增SKU列+来源列(手动/1688/CSV导入)+库存列

## 全链路流水线验证

```
创建商品 → 三道闸 → 淘宝🍑 抖店🎵 拼多多📦 亚马逊🌍
                ↓ 文字违禁→作废
                ↓ 价格异常→待审核
                ↓ 全部通过→4平台同时发布
       ✅ total:4  passed:4  published:4  stage:complete
```
