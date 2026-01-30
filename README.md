
---

# 医院药品管理系统 (Hospital Medicine Management System)

本项目是一款基于 Django 与 Vue 3 构建的前后端分离管理平台。系统专注于医院药房的日常业务逻辑，涵盖了药品入库、用药追踪、多维度智能预警及数据可视化分析，旨在提升药房管理效率与安全性。

## 🛠️ 技术栈

* **后端**: Python 3.x + Django + Django REST Framework (DRF)
* **前端**: Vue 3 + Vite + Element Plus + Echarts
* **数据库**: SQLite (默认)

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

# 3. 创建系统管理员账号 (根据提示设置用户名与密码)
python manage.py createsuperuser

# 4. 开启后端服务
python manage.py runserver

```

* **访问地址**: `http://127.0.0.1:8000/`

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

* **访问地址**: `http://localhost:3000` (具体端口请以终端输出为准)

---

## 📂 核心功能模块
* **数据看板**: 集成 Echarts 图表，直观展示药品消耗趋势、库存周转率等关键指标，辅助管理决策。
* **药品管理**: 完整的库存 CRUD 体系，具备动态颜色标识，实时反映药品状态（如：库存正常、库存不足）。
* **智能预警**: 系统自动扫描并识别“库存紧缺”及“近效期”（30天内过期）药品，主动防范风险。
* **用药记录**: 详尽的领药流水追踪，支持根据时间、药品名等维度进行快速回溯查询。
* **用户管理**: 完善的权限控制，保障系统数据录入与查询的安全可靠。

---
