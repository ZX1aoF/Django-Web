# Django-Web

> 基于 Django 的「学生 / 管理员信息管理系统」——支持身份选择、注册、登录与个人信息维护。

![Django](https://img.shields.io/badge/Django-4.1.12-092E20?logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8%20~%203.11-3776AB?logo=python&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
- [账号规则](#账号规则)
- [页面与路由](#页面与路由)
- [数据模型](#数据模型)
- [已知问题与改进方向](#已知问题与改进方向)
- [安全说明](#安全说明)
- [License](#license)

## 项目简介

Django-Web 是一个课程实践项目（项目配置包名为 `SE`），实现了一个校园信息管理系统的**最小可用形态**：用户分为「学生」与「管理员」两种身份，可以使用 10 位账号注册、登录，登录后进入资料页并维护自己的信息。

账号由「年级（4 位）+ 编号（6 位）」拼接而成。注册时只需填写年级，系统会自动为该年级分配下一个可用编号。

> `material`（资料）应用目前只有一个导航占位页，尚未实现具体业务功能，详见[已知问题与改进方向](#已知问题与改进方向)。

## 功能特性

| 功能 | 说明 |
| --- | --- |
| 身份分流 | 首页选择「学生 / 管理员」，进入对应登录 / 注册流程 |
| 注册 | 填写姓名、性别、生日、邮箱、个人简介；密码二次确认；学号 / 编号自动分配 |
| 登录 | 10 位账号 + 密码，登录状态保存在 session 中 |
| 个人信息维护 | 登录后可修改除年级、编号以外的所有字段 |
| 退出登录 | 清空 session 并回到首页 |
| 表单校验 | 账号长度、账号是否不存在、密码是否正确等错误提示 |

## 技术栈

| 分类 | 选型 |
| --- | --- |
| 语言 | Python 3.8 ~ 3.11（推荐 3.10 / 3.11） |
| 框架 | Django 4.1.12 |
| 数据库 | SQLite 3 |
| 模板 | Django Template Language |
| 样式 | 手写 CSS（`static/css/`） |
| 前端框架 | 无 |

> Django 4.1 已于 2023 年 12 月结束官方支持（EOL）。如需长期维护，建议升级到 4.2 LTS 或更高版本。

## 目录结构

```text
Django-Web/
├── SE/                     # 项目配置包（settings / urls / wsgi / asgi）
│   ├── settings.py
│   └── urls.py
├── user/                   # 用户应用：注册、登录、信息修改
│   ├── models.py           # Student / Administrator 模型
│   ├── forms.py            # 登录、注册、修改表单
│   ├── cbvs.py             # 基于类的视图（注册、修改）
│   ├── views.py            # 基于函数的视图（首页、登录、登出、分发）
│   ├── urls.py
│   ├── constants.py
│   └── migrations/
├── material/               # 资料应用（当前仅有占位导航页）
│   ├── views.py
│   ├── urls.py
│   └── migrations/
├── templates/
│   ├── user/               # login_home / login_detail / register / register_home / update / background
│   └── material/
│       └── nav.html
├── static/
│   └── css/                # login.css / register.css / nav.css
├── manage.py
├── requirements.txt
├── .gitignore
└── LICENSE
```

## 快速开始

### 1. 克隆并创建虚拟环境

```bash
git clone https://github.com/ZX1aoF/Django-Web.git
cd Django-Web

python -m venv .venv
```

激活虚拟环境：

```bash
# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 初始化数据库

```bash
python manage.py migrate
```

> `db.sqlite3` 已从版本控制中移除（它是本地开发数据库，会随时变化）。首次运行**必须**先执行上面的 `migrate` 命令来生成表结构，否则会报 `no such table`。

### 4. 启动开发服务器

```bash
python manage.py runserver
```

浏览器打开 <http://127.0.0.1:8000/> 即可看到首页。

> 修正说明：旧版 README 中写的 `cd SE` 与 `manager.py` 均为笔误——`manage.py` 位于**仓库根目录**，请在根目录执行。

### 5.（可选）使用 Django Admin

```bash
python manage.py createsuperuser
```

然后访问 <http://127.0.0.1:8000/admin/>。注意：目前 `user/admin.py` 与 `material/admin.py` 都没有注册任何模型，因此后台里看不到业务数据。

## 账号规则

- 账号 = **年级（4 位） + 编号（6 位）**，合计 **10 位**
- 示例：年级 `2023` + 编号 `000001` → 账号 `2023000001`
- 登录时输入这 10 位账号与密码；系统按前 4 位解析年级、后 6 位解析编号来定位用户
- 注册时只需填写年级，编号由系统取该年级当前最大编号 + 1 自动分配（该年级无记录时从 `000001` 开始）
- 同一身份下 `(年级, 编号)` 唯一，数据库层有唯一约束保证

> 提示：`uid` 长度不等于 10 位时，登录表单会直接提示「账号必须为 10 位数」。

## 页面与路由

| 路由 | 视图 | 说明 |
| --- | --- | --- |
| `/` | `user.views.home` | 登录首页，选择「学生 / 管理员」身份 |
| `/user/login/` | `user.views.home` | 与首页相同（具名路由 `login`） |
| `/user/login/<kind>` | `user.views.login` | 登录表单页 / 提交处理，`kind` ∈ `student` \| `administrator` |
| `/user/logout/` | `user.views.logout` | 退出登录，清空 session |
| `/user/register/` | `user.views.register_home` | 选择注册身份 |
| `/user/register/<kind>` | `user.views.register` | 注册表单页 / 提交处理 |
| `/user/update/<kind>` | `user.views.update` | 修改个人信息（需已登录） |
| `/material/<kind>/` | `material.views.home` | 登录后的资料页（当前为占位导航） |

其中 `kind` 只接受 `student` 与 `administrator` 两个值，其余值统一返回「Invalid kind」提示。

## 数据模型

两个模型都定义在 `user/models.py` 中，字段结构完全一致，区别仅在语义与唯一约束名。

### Student（学生）

| 字段 | 类型 | verbose_name | 说明 |
| --- | --- | --- | --- |
| `name` | `CharField(50)` | 姓名 | |
| `gender` | `CharField(10)` | 性别 | `choices`：`m` = 男、`f` = 女，默认 `m` |
| `birthday` | `DateField` | 生日 | |
| `email` | `EmailField` | 邮箱 | |
| `info` | `CharField(255)` | 个人简介 | `help_text`：一句话介绍自己 |
| `grade` | `CharField(4)` | 年级 | |
| `number` | `CharField(6)` | 学号 | 自动分配 |
| `password` | `CharField(30)` | 密码 | 明文存储，见[安全说明](#安全说明) |

唯一约束：`UniqueConstraint(fields=['grade', 'number'], name='student_id')`

### Administrator（管理员）

字段同上，仅两处不同：

- `number` 的 `verbose_name` 为「编号」
- 唯一约束名为 `administrator_id`

两个模型都提供了 `get_id()` 方法，返回 `grade + number`，即登录时使用的 10 位账号；`__str__()` 返回 `账号 (姓名)` 形式，便于在 Admin 与 shell 中辨认。

## 已知问题与改进方向

以下问题是在通读源码后整理出来的，**当前代码均未修复**，按优先级排列，可作为后续迭代的 TODO 清单。

| 优先级 | 位置 | 问题 | 建议 |
| --- | --- | --- | --- |
| 高 | `material/views.py` | `get_user()` 的身份白名单写成了 `["student", "teacher"]`，但项目实际角色是 `administrator`。管理员登录后会被判定为非法身份，不断重定向回登录页，形成死循环 | 改为 `["student", "administrator"]` |
| 高 | `material/views.py` | `Administrator.objects.filter(department_no=grade)` 使用了模型中不存在的字段 `department_no`，一旦走到该分支会抛 `FieldError` | 改为 `filter(grade=grade)` |
| 高 | `user/views.py` + `user/forms.py` | 管理员登录表单的字段名是 `aid`，但 `login()` 视图统一读取 `form.cleaned_data["uid"]`，管理员登录会直接 `KeyError` | 统一字段名为 `uid`，或按 `kind` 分别取值 |
| 高 | `user/forms.py` | 两个注册表单的 `clean()` 方法被写在了 `class Meta` **内部**（缩进错误），导致「确认密码」校验从未真正执行；此外 `AdmRegisterForm.clean` 内还错误地引用了 `StuRegisterForm` | 把 `clean()` 移到表单类层级，并修正类名引用 |
| 中 | `user/cbvs.py` | `CreateAdministratorView.form_valid()` 中用 `Student.objects` 来查询最大编号，导致管理员编号与学生编号互相干扰、可能撞号 | 改用 `Administrator.objects` |
| 中 | 全局 | 密码以明文形式存储与比对，完全没有使用 `django.contrib.auth` | 改用 `create_user()` / `check_password()`，并迁移历史数据 |
| 中 | `SE/settings.py` | `SECRET_KEY` 硬编码并提交进仓库；`DEBUG = True`；`ALLOWED_HOSTS = []` | 改为从环境变量读取，生产环境关闭 DEBUG 并配置 ALLOWED_HOSTS |
| 中 | `user/views.py` | 顶部 `from audioop import reverse` —— `audioop` 模块已在 **Python 3.13 中被移除**，会导致项目在 3.13 上直接启动失败（`ModuleNotFoundError`） | 删除该行，改用 `from django.urls import reverse` |
| 低 | 多处 | 一批无用 import：`multiprocessing.context`、`pydoc.cram`、`django.urls.is_valid_path`、`decimal.MAX_EMAX`、`dataclasses.fields` 等 | 逐一清理，可借助 `ruff` / `flake8` |
| 低 | `SE/urls.py` + `user/urls.py` | 两处 urlconf 都定义了名为 `login` 的路由，反向解析结果存在歧义 | 重命名其中一处，例如首页改为 `index` |
| 低 | `material/` | 该应用只有 `nav.html` 一个占位页，没有模型与业务逻辑 | 按需求补全资料管理功能 |
| 低 | `user/admin.py` | `django.contrib.admin` 已启用，但没有注册任何模型 | 注册 `Student` / `Administrator`，或移除该应用 |
| 低 | `user/tests.py`、`material/tests.py` | 仍是 Django 默认的空测试模板，项目没有测试覆盖 | 补充模型与视图测试 |

## 安全说明

本项目定位为**教学 / 课程作业**，请勿直接部署到生产环境。目前存在以下安全风险：

1. **密码明文存储**：数据库中的 `password` 字段直接保存明文，登录时做字符串比对，任何能读到数据库的人都能拿到所有用户的密码
2. **密钥泄漏**：`SECRET_KEY` 硬编码在 `settings.py` 中并提交进仓库，任何人都可以为该站点伪造 session
3. **调试模式**：`DEBUG = True`，出错时会向访问者暴露源码、路径与配置片段

如需对外发布，请先完成[已知问题](#已知问题与改进方向)中标记为「高」与「中」的改造。

## License

本项目基于 [MIT License](LICENSE) 开源。
