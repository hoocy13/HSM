# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在本仓库中工作时提供指引。

## 项目概述

医院药品管理系统 — 前后端分离的全栈 Web 应用，涵盖药品库存管理、处方开具、发药审批流程、智能预警及数据可视化看板。

## 技术栈

- **后端**: Python 3 + Django 4.2 + Django REST Framework, SQLite (默认)
- **前端**: Vue 3 + Vite + Element Plus + ECharts 6
- **认证**: 自定义 `SimpleTokenAuthentication` — token 格式为 `simple_token_<user_id>`，通过 `Authorization: Bearer <token>` 请求头传递

## 常用命令

### 后端 (项目根目录)
```bash
python manage.py makemigrations    # 生成迁移文件
python manage.py migrate           # 执行数据库迁移
python manage.py create_admin      # 创建/重置管理员账号 (admin/admin)
python manage.py import_meds --skip-drugs --reset-enhancements --start-date 2025-08-01 --end-date 2026-05-15  # 生成演示数据
python manage.py runserver         # 启动后端服务 http://127.0.0.1:8000/
python manage.py check             # Django 自检
```

### 前端 (frontend/ 目录)
```bash
npm install
npm run dev        # 开发服务器 http://localhost:3000 (代理 /api → Django)
npm run build      # 生产构建
```

## 架构

### 后端 (`hospital_sys/` + `drugs/`)

单一 Django 应用 `drugs` 包含全部业务逻辑，项目配置位于 `hospital_sys/`。

**核心模块：**
- `drugs/models.py` — 全部模型：`Drug`（药品）、`MedicationRecord`（处方/用药记录）、`UserProfile`（角色：admin/doctor/pharmacist）、`InventoryAdjustment`（库存盘点）、`OperationLog`（操作审计）、`Alert`（预警）、`Announcement`（公告）、`Policy`（政策）
- `drugs/views.py` — 全部视图集：`DrugViewSet`、`MedicationRecordViewSet`、`AuthViewSet`、`UserViewSet`、`DashboardViewSet`、`AnnouncementViewSet`、`OperationLogViewSet`、`InventoryAdjustmentViewSet`
- `drugs/serializers.py` — DRF 序列化器及校验逻辑
- `drugs/authentication.py` — `SimpleTokenAuthentication`（从 `simple_token_<id>` token 中提取用户 ID）
- `drugs/permissions.py` — 基于角色的权限类：`IsAdmin`、`IsDoctor`、`IsPharmacist`、`IsAdminOrPharmacist`、`IsAdminOrDoctor`。`_role(user)` 工具函数用于全局获取用户角色
- `drugs/dashboard_service.py` — 看板数据构建器：`build_home_payload`、`build_trends_payload`、`build_recommendations_payload`、`_scope_med_qs`（科室数据隔离）
- `drugs/services/alert_service.py` — 库存/效期变更及疾病趋势异常时写入 `Alert`
- `drugs/services/log_service.py` — `log_operation()` 在事务内写入 `OperationLog`
- `drugs/services/stock_trend_service.py` — 根据库存调整和处方记录重建单药品库存时间线
- `drugs/pagination.py` — `StandardResultsSetPagination`（page_size=10, max 2000）

**管理命令** (`drugs/management/commands/`)：
- `create_admin` — 创建/更新管理员账号 (admin/admin)
- `import_meds` — 从 CSV 导入药品并生成模拟用药记录、库存流水、预警
- `update_prescription_ids` — 回填处方号工具

**发药流程**：医师开具处方（状态=pending，不扣库存）→ 药剂师审批发药（`dispense` 动作，扣减库存）或拒绝（`reject_pending`）。支持撤销发药和作废处方，均会回滚库存。

**科室隔离**：医师和药剂师仅可查看本科室数据，管理员可查看全院数据。通过 `_scope_med_qs()` 和 ViewSet 中的 `_role()` 检查实现。

### 前端 (`frontend/src/`)

- `api/drugs.js` — 全部 API 客户端函数，基于 axios（baseURL: `http://127.0.0.1:8000/api`），按业务域组织：`drugApi`、`medicationApi`、`authApi`、`userApi`、`dashboardApi`、`inventoryApi`、`operationLogApi`、`announcementApi`
- `router/index.js` — 路由定义及角色守卫（`meta.roleRequired`）。所有需认证路由位于 `/layout` 下，`index.vue` 作为布局外壳
- `layout/index.vue` — 侧边栏导航，菜单项按角色条件渲染
- `views/` — 页面组件：`DashboardHome`（工作台）、`DataOverview`（数据概览）、`DataTrends`（数据趋势）、`DataRelations`（关联关系图）、`DrugList`（药品列表）、`MedicationRecords`（用药记录）、`DispenseApprove`（审批发药）、`UserManagement`（员工管理）、`OperationLogs`（操作审计）、`AnnouncementManage`（系统公告）等
- `components/` — 角色专属看板组件（`DoctorDashboardWidgets`、`PharmacistDashboardWidgets`）

**前端认证**：Token 存储于 `localStorage` 的 `token` 键，用户对象存储于 `user` 键。axios 拦截器为每个请求附加 `Authorization: Bearer <token>`。路由守卫检查 token 存在性和角色权限。

### API 结构

全部端点通过 DRF 路由器挂载于 `/api/` 下：
- `/api/drugs/` — CRUD + `/stock-in/`（入库）、`/warnings/`（预警）、`/stock-trend/`（库存趋势）
- `/api/medication-records/` — CRUD + `/dispense/`（发药）、`/reject-pending/`（拒绝）、`/undo-dispense/`（撤销发药）、`/cancel/`（作废处方）、`/department-users/`（科室用户）
- `/api/inventory-adjustments/` — 库存盘点/损溢
- `/api/dashboard/` — `/stats/`（统计）、`/trends/`（趋势）、`/recommendations/`（推荐）、`/consumption-trend/`（消耗预测）、`/drug-correlation/`（药品关联）、`/low-stock-top10/`（库存紧缺 Top10）、`/expiry-distribution/`（效期分布）、`/monthly-consumption/`（月度消耗）、`/top5-correlated/`（高频联用 Top5）
- `/api/auth/` — `/login/`（登录）、`/logout/`（登出）
- `/api/users/` — CRUD + `/activate/`（启用）、`/deactivate/`（停用）
- `/api/operation-logs/` — 只读操作审计日志
- `/api/announcements/` — 仅管理员可操作的公告 CRUD

看板接口支持 `days=N` 或 `date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` 进行时间窗口筛选。

## 关键设计模式

- 库存变更始终在 `transaction.atomic()` 内使用 `select_for_update()` 防止并发竞争
- `log_operation()` 在业务事务内同步调用，与业务写入同属一个事务
- 库存变更后调用 `maybe_alerts_for_drug()` 写入 LOW_STOCK/EXPIRY 预警
- `UserProfile` 通过 OneToOneField 扩展 Django `User`；`post_save` 信号自动创建用户资料
- 用户删除为软删除 — `deactivate` 设置 `is_active=False` 而非物理删除
- 每个 `prescription_id` 仅允许对应一种药品（一条记录）
