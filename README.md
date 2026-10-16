# Django-Web

> 基于 Django 的「学生 / 管理员信息管理系统」——支持身份选择、注册、登录与个人信息维护。

![Django](https://img.shields.io/badge/Django-4.1.12-092E20?logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8%20~%203.13-3776AB?logo=python&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![Tests](https://img.shields.io/badge/tests-39%20passed-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
- [环境变量](#环境变量)
- [运行测试](#运行测试)
- [账号规则](#账号规则)
- [页面与路由](#页面与路由)
- [数据模型](#数据模型)
- [修复记录](#修复记录)
- [后续可做](#后续可做)
- [安全说明](#安全说明)
- [License](#license)

## 项目简介

Django-Web 是一个课程实践项目（项目配置包名为 `SE`），实现了一个校园信息管理系统的**最小可用形态**：用户分为「学生」与「管理员」两种身份，可以使用 10 位账号注册、登录，登录后进入资料页并维护自己的信息。

账号由「年级（4 位）+ 编号（6 位）」拼接而成。注册时只需填写年级，系统会自动为该年级分配下一个可用编号。

> `material`（资料）应用目前只有一个导航占位页，尚未实现具体业务功能，详见[后续可做](#后续可做)。

## 功能特性

| 功能 | 说明 |
| --- | --- |
| 身份分流 | 首页选择「学生 / 管理员」，进入对应登录 / 注册流程 |
| 注册 | 填写姓名、性别、生日、邮箱、个人简介；密码二次确认；学号 / 编号自动分配 |
| 密码安全 | 密码经 PBKDF2-SHA256 哈希后入库，校验使用恒定时间比较，不再保存明文 |
| 登录 | 10 位账号 + 密码，登录状态保存在 session 中 |
| 个人信息维护 | 登录后可修改除年级、编号以外的所有字段 |
| 退出登录 | 清空并轮换 session，回到首页 |
| 表单校验 | 账号长度、账号是否不存在、密码是否正确、两次密码是否一致等提示 |
| 后台管理 | `/admin/` 已挂载，`Student` / `Administrator` 已注册到 Django Admin |
| 测试 | 39 个用例覆盖注册、登录、改资料、资料页与表单校验 |

## 技术栈

| 分类 | 选型 |
| --- | --- |
| 语言 | Python 3.8 ~ 3.13（已在 3.13 上实测通过） |
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
│   ├── models.py           # Person 抽象基类 + Student / Administrator
│   ├── forms.py            # 登录、注册、修改表单 + 密码哈希 Mixin
│   ├── cbvs.py             # 基于类的视图（注册、修改）
│   ├── views.py            # 基于函数的视图（首页、登录、登出、分发）
│   ├── admin.py            # Django Admin 注册
│   ├── constants.py        # 账号长度、身份标识等常量
│   ├── tests.py            # 回归测试
│   ├── urls.py
│   └── migrations/
│       ├── 0001_initial.py
│       ├── 0002_widen_password_field.py
│       └── 0003_hash_plaintext_passwords.py
├── material/               # 资料应用（当前仅有占位导航页）
│   ├── views.py
│   ├── tests.py
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

> 国内网络直连 PyPI 可能很慢，可以换镜像：
> `pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/`

### 3. 初始化数据库

```bash
python manage.py migrate
```

> `db.sqlite3` 已从版本控制中移除（它是本地开发数据库，会随时变化）。首次运行**必须**先执行上面的 `migrate` 命令来生成表结构，否则会报 `no such table`。
>
> 迁移 `0003` 会把库里已有的**明文**密码批量转换成哈希，转换后原密码依然可以正常登录。

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

然后访问 <http://127.0.0.1:8000/admin/>，可以在后台直接查看 / 编辑学生与管理员记录（密码字段已从后台表单中排除）。

## 环境变量

`SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS` 都从环境变量读取，未设置时使用仅适合本地开发的默认值。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | 内置的开发用占位密钥 | 生产环境**必须**注入随机值 |
| `DJANGO_DEBUG` | `1` | 设为 `0` 关闭调试模式 |
| `DJANGO_ALLOWED_HOSTS` | 空 | 逗号分隔，例如 `example.com,www.example.com` |

调试模式下若未指定 `ALLOWED_HOSTS`，会自动允许 `127.0.0.1` / `localhost` / `[::1]`。

```bash
# 例如在 Linux 上以生产参数启动
export DJANGO_SECRET_KEY='换成你自己的随机串'
export DJANGO_DEBUG=0
export DJANGO_ALLOWED_HOSTS='example.com'
```

## 运行测试

```bash
python manage.py test
```

共 39 个用例，覆盖注册编号分配、密码哈希、两种身份的登录、资料修改、资料页访问控制与表单校验。

## 账号规则

- 账号 = **年级（4 位） + 编号（6 位）**，合计 **10 位**
- 示例：年级 `2023` + 编号 `000001` → 账号 `2023000001`
- 登录时输入这 10 位账号与密码；系统按前 4 位解析年级、后 6 位解析编号来定位用户
- 注册时只需填写年级，编号由系统取该年级当前最大编号 + 1 自动分配（该年级无记录时从 `000001` 开始）
- 同一身份下 `(年级, 编号)` 唯一，数据库层有唯一约束保证
- 学生与管理员的编号各自独立递增，互不影响

> 提示：账号长度不等于 10 位时，登录表单会直接提示「账号必须为 10 位数」。

## 页面与路由

| 路由 | 视图 | 说明 |
| --- | --- | --- |
| `/` | `user.views.home` | 首页，选择「学生 / 管理员」身份（路由名 `index`） |
| `/user/login/` | `user.views.home` | 与首页相同（路由名 `login`） |
| `/user/login/<kind>` | `user.views.login` | 登录表单页 / 提交处理（路由名 `login_detail`） |
| `/user/logout/` | `user.views.logout` | 退出登录，清空 session |
| `/user/register/` | `user.views.register_home` | 注册身份选择页（路由名 `register`） |
| `/user/register/<kind>` | `user.views.register` | 注册表单页 / 提交处理（路由名 `register_detail`） |
| `/user/update/<kind>` | `user.views.update` | 修改个人信息（需已登录） |
| `/material/<kind>/` | `material.views.home` | 登录后的资料页（当前为占位导航） |
| `/admin/` | Django Admin | 后台管理 |

`kind` 只接受 `student` 与 `administrator`，其余值统一返回 **400** 与一句「身份参数无效」的提示。

## 数据模型

`user/models.py` 中定义了一个抽象基类 `Person`，`Student` 与 `Administrator` 继承它，只覆盖 `number` 字段的中文名与各自的唯一约束名。

`Person` 提供的公共能力：

- `get_id()` —— 返回 `年级 + 编号`，即登录用的 10 位账号
- `set_password(raw)` —— 用 `make_password()` 生成 PBKDF2-SHA256 哈希
- `check_password(raw)` —— 用 `check_password()` 做恒定时间校验
- `__str__()` —— 返回 `账号 (姓名)`，便于在 Admin 与 shell 中辨认

### 字段

| 字段 | 类型 | verbose_name | 说明 |
| --- | --- | --- | --- |
| `name` | `CharField(50)` | 姓名 | |
| `gender` | `CharField(10)` | 性别 | `choices`：`m` = 男、`f` = 女，默认 `m` |
| `birthday` | `DateField` | 生日 | |
| `email` | `EmailField` | 邮箱 | |
| `info` | `CharField(255)` | 个人简介 | `help_text`：一句话介绍自己 |
| `grade` | `CharField(4)` | 年级 | |
| `number` | `CharField(6)` | 学号 / 编号 | 注册时自动分配，不可修改 |
| `password` | `CharField(128)` | 密码 | 存放 PBKDF2-SHA256 哈希，不是明文 |

- `Student` 唯一约束：`UniqueConstraint(grade, number)`，名为 `student_id`
- `Administrator` 唯一约束：`UniqueConstraint(grade, number)`，名为 `administrator_id`

## 修复记录

以下缺陷已在 2026-10 的一次集中修复中处理完毕，测试用例覆盖了每一条。

| 优先级 | 位置 | 问题 | 处理方式 |
| --- | --- | --- | --- |
| 高 | `material/views.py` | 身份白名单写成 `["student", "teacher"]`，管理员登录后被判为非法身份，无限重定向回登录页 | 改用统一的 `KINDS` 常量（`student` / `administrator`） |
| 高 | `material/views.py` | 查询用了不存在的字段 `department_no`，会抛 `FieldError` | 改为按 `grade` + `number` 查询 |
| 高 | `user/forms.py` + `user/views.py` | 管理员登录表单字段名为 `aid`，视图却统一读 `cleaned_data["uid"]`，管理员登录直接 `KeyError` | 两个登录表单统一使用 `uid` |
| 高 | `user/forms.py` | 两个注册表单的 `clean()` 被写在 `class Meta` 内部，确认密码校验从未执行；`AdmRegisterForm.clean` 还错误引用了 `StuRegisterForm` | 校验逻辑上移到 `PersonRegisterForm` 表单类层级 |
| 高 | `user/cbvs.py` | `CreateAdministratorView` 用 `Student` 表计算下一个编号，管理员编号会与学生撞号 | 编号分配改为基于 `self.model` |
| 中 | 全局 | 密码以明文存储与比对 | 改为 `make_password` / `check_password`，并提供数据迁移转换历史数据 |
| 中 | `SE/settings.py` | `SECRET_KEY` 硬编码进仓库、`DEBUG=True` 硬编码 | 三者全部改为从环境变量读取 |
| 中 | `user/views.py` | `from audioop import reverse` —— `audioop` 已在 Python 3.13 中移除，项目无法在 3.13 上启动 | 删除，改用 `django.urls.reverse` |
| 中 | `user/forms.py` | `AdmRegisterForm` 未声明 `password` 字段，ModelForm 把它渲染成明文输入框 | 在基类中统一声明为 `PasswordInput` |
| 中 | `templates/user/login_detail.html` | 块名写成 `welcome-message`，与父模板的 `welcome_message` 不匹配，注册成功提示从未渲染 | 改为 `welcome_message` |
| 中 | `user/cbvs.py` | 管理员的修改表单沿用了注册表单，年级可改 —— 而年级参与账号拼接，改完账号就变了 | 新增 `AdmUpdateForm`，与 `StuUpdateForm` 一样收起年级 |
| 低 | 多处 | 无用 import：`multiprocessing.context`、`pydoc.cram`、`is_valid_path`、`decimal.MAX_EMAX`、`dataclasses.fields`、`random` 等 | 全部清理 |
| 低 | `SE/urls.py` + `user/urls.py` | 两处 urlconf 都定义了名为 `login` 的路由，反向解析靠参数个数区分，含义含糊 | 首页改名 `index`，带身份的路由改名 `login_detail` / `register_detail` |
| 低 | `SE/urls.py` | `import admin` 却没挂路由，`/admin/` 一直是 404 | 补上 `path("admin/", admin.site.urls)` |
| 低 | `user/admin.py` | 后台未注册任何模型 | 注册 `Student` / `Administrator`，并从后台表单排除密码字段 |
| 低 | `material/views.py` | `student_home` 与 `administrator_home` 两份完全重复的代码 | 合并为单个 `home` 视图 |
| 低 | `user/tests.py`、`material/tests.py` | 仍是 Django 默认空模板，没有测试覆盖 | 补充 39 个回归测试 |
| 低 | `SE/settings.py` | `LANGUAGE_CODE='en-us'` / `TIME_ZONE='UTC'`，与全中文界面不一致，Django 内置校验提示是英文 | 改为 `zh-hans` / `Asia/Shanghai` |
| 低 | `templates/user/update.html` | 重复 `{% load static %}` 与重复 `<link>`；标题误写成 “Register” | 清理并改为「修改个人信息」 |

## 后续可做

- **补齐 `material` 功能**：该应用目前只有导航页，没有模型与业务逻辑
- **密码强度校验**：`settings.py` 里的 `AUTH_PASSWORD_VALIDATORS` 目前没有生效（这两个模型不是 `auth.User`），可在表单里显式调用 `validate_password()`
- **注册并发**：编号分配是「查最大值 + 1」，并发注册同一届时会撞唯一约束，可改用重试或数据库序列
- **升级 Django**：4.1 已 EOL，建议升到 4.2 LTS
- **补 CI**：加上 GitHub Actions 跑 `manage.py test`

## 安全说明

本项目定位为**教学 / 课程作业**，请勿直接部署到生产环境。已修复的部分与仍存在的注意事项：

**已修复**

1. 密码不再以明文入库，改用 Django 的 PBKDF2-SHA256 哈希
2. `SECRET_KEY` 不再硬编码，改为从环境变量读取
3. `DEBUG` 可通过环境变量关闭
4. 退出登录改为 `session.flush()`，同时清空数据并轮换 session key

**仍需注意**

1. 调试模式默认开启，线上务必设置 `DJANGO_DEBUG=0`
2. 项目没有做 CSRF 之外的访问控制加固，也没有限流，登录接口可被暴力尝试
3. 密码只做了哈希，没有做强度校验（见[后续可做](#后续可做)）
4. 注意：早期提交历史里的 `SECRET_KEY` 已经泄漏，如曾有线上部署，请务必更换

## License

本项目基于 [MIT License](LICENSE) 开源。
