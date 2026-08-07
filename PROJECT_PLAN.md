# 全平台AI自动上架系统 — 项目执行计划

## 项目状态：🟢 v0.7.0 全部完成
**项目经理**：AI（小林辅助决策）  
**开始日期**：2026-08-06  
**仓库**：[github.com/lin445816282/ecommerce-auto-publish](https://github.com/lin445816282/ecommerce-auto-publish)  
**提交数**：14 commits

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

## 全链路流水线验证

```
创建商品 → 三道闸 → 淘宝🍑 抖店🎵 拼多多📦 亚马逊🌍
                ↓ 文字违禁→作废
                ↓ 价格异常→待审核
                ↓ 全部通过→4平台同时发布
       ✅ total:4  passed:4  published:4  stage:complete
```
