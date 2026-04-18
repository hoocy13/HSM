# 医院药品管理系统 (Hospital Medicine Management System)

本项目是一款基于 Django 与 Vue 3 构建的前后端分离管理平台。系统专注于医院药房的日常业务逻辑，涵盖了药品入库、用药追踪、多维度智能预警及数据可视化分析，旨在提升药房管理效率与安全性。

## 🛠️ 技术栈

- **后端**: Python 3.x + Django + Django REST Framework (DRF)
- **前端**: Vue 3 + Vite + Element Plus + Echarts
- **数据库**: SQLite (默认)
- **认证**: Token（前端使用 `Authorization: Bearer <token>`；演示环境默认形如 `simple_token_<user_id>`）

---

## 🚀 快速启动指引

### 1. 获取项目代码

首先，将项目克隆至本地并进入工作目录：

```bash
# 克隆仓库
git clone <你的仓库地址>
cd HSM

```

### 2. 后端环境配置 (Django)

在 PyCharm 终端或系统命令行中执行以下步骤：

```bash
# 1. 安装项目运行所需的依赖环境
# 如果你还没有 requirements.txt，可以直接安装核心包：
pip install django djangorestframework django-cors-headers

# 2. 初始化数据库结构
python manage.py makemigrations
python manage.py migrate

# 3. 创建/更新默认管理员账号（推荐，用于演示）
python manage.py create_admin

# 4. （可选）导入药品并生成演示数据
# - 默认只要有药品数据即可生成用药记录、库存流水与预警
# - 支持覆盖到指定日期（示例覆盖到 2026-05-15）
python manage.py import_meds --skip-drugs --reset-enhancements --start-date 2025-08-01 --end-date 2026-05-15

# 5. 开启后端服务
python manage.py runserver

```

- **访问地址**: `http://127.0.0.1:8000/`
- **Admin 后台**: `http://127.0.0.1:8000/admin/`

### 3. 前端环境配置 (Vue 3)

请开启一个新的终端窗口进行前端调试：

```bash
# 1. 切换至前端工程目录
cd frontend

# 2. 安装项目依赖组件
npm install

# 3. 启动前端开发服务器
npm run dev

```

- **访问地址**: `http://localhost:3000` (具体端口请以终端输出为准)

---

## 📂 核心功能模块

- **数据看板**: 集成 ECharts 图表，支持近 7/30/90 天时间窗口，包含用药趋势、疾病趋势、药品关联矩阵、药品关联关系网、推荐用药等，用于演示与决策。
- **药品管理**: 完整的库存 CRUD 体系，具备动态颜色标识，实时反映药品状态（如：库存正常、库存不足）。
- **智能预警**: 系统自动扫描并识别“库存紧缺”及“近效期”（30天内过期）药品，主动防范风险。
- **用药记录**: 详尽的领药流水追踪，支持根据时间、药品名等维度进行快速回溯查询。
- **用户管理**: 完善的权限控制，保障系统数据录入与查询的安全可靠。
- **操作审计**: 关键业务操作记录到 `OperationLog`，仅管理员可在“操作审计”页面查看与筛选。
- **科室隔离**: 医生/药剂师默认仅查看自己科室范围数据，管理员可查看全院数据。

---

## 🧪 演示数据（推荐流程）

### 1) 导入药品（可选）

如果你项目根目录有 `meds.csv`（每行一个药品名称），可以执行：

```bash
python manage.py import_meds --file meds.csv
```

### 2) 生成/重置演示数据（覆盖到 2026-05-15）

会清理并重建：`MedicationRecord`、`InventoryAdjustment`、`Alert`、`OperationLog`，并重置库存，适合反复演示。

```bash
python manage.py import_meds --skip-drugs --reset-enhancements --start-date 2025-08-01 --end-date 2026-5-15
```

### 3) 演示账号

默认管理员账号（由 `create_admin` 命令创建/更新）：

- **username**: `admin`
- **password**: `admin`

---

## 📊 看板接口口径（演示级）

### 时间窗口（统一口径）

看板页面默认近 **30 天**，可切换 7/30/90 天。后端接口支持：

- `days=30`（默认）
- 或 `date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`

示例：

```bash
GET /api/dashboard/trends/?days=30
GET /api/dashboard/stats/?days=30
```

---

## 🗺️ 前端页面入口（管理员视角）

- **工作台**：`/layout/dashboard`
- **数据看板**
  - 数据概览：`/layout/data-overview`
  - 数据趋势：`/layout/data-trends`
  - 关联关系图：`/layout/data-relations`
- **操作审计**：`/layout/operation-logs`（admin）
- **药品管理**：`/layout/drugs`

---

## 🛠️ 常用命令速查

```bash
# 后端自检
python manage.py check

# 前端构建验证
cd frontend && npm run build

```

