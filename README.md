# Django-Web

> 基于 Django 的「语文素材管理系统」——管理员维护素材，学生检索与投稿。

![Django](https://img.shields.io/badge/Django-4.1.12-092E20?logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8%20~%203.13-3776AB?logo=python&logoColor=white)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![Tests](https://img.shields.io/badge/tests-95%20passed-brightgreen)
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
- [素材库](#素材库)
- [界面设计](#界面设计)
- [数据模型](#数据模型)
- [修复记录](#修复记录)
- [后续可做](#后续可做)
- [安全说明](#安全说明)
- [License](#license)

## 项目简介

Django-Web 是一个课程实践项目（项目配置包名为 `SE`），实现了「语文素材管理系统」：

- **两种身份**：学生与管理员，用 10 位账号注册、登录
- **素材库**：管理员录入 / 编辑 / 删除语文素材（支持正文与附件），学生检索与阅读
- **投稿与审核**：学生也能投稿，稿件经管理员审核通过后才进入公共素材库
- **账号规则**：账号 = 年级（4 位）+ 编号（6 位），注册时自动分配编号

## 功能特性

| 模块 | 功能 |
| --- | --- |
| 身份 | 首页选择「学生 / 管理员」，进入对应登录 / 注册流程 |
| 注册 | 姓名、性别、生日、邮箱、简介 + 密码二次确认，编号自动分配 |
| 密码安全 | PBKDF2-SHA256 哈希存储 + 强度校验（长度 / 纯数字 / 常见密码 / 与邮箱过于相似） |
| 登录 | 10 位账号 + 密码，登录状态保存在 session 中 |
| 个人信息 | 登录后可修改除年级、编号以外的字段 |
| 素材库 | 列表、分类筛选、关键词搜索、详情阅读、附件下载 |
| 学生投稿 | 学生可投稿并附附件，稿件默认「待审核」，通过后才进入公共素材库 |
| 审核 | 管理员按状态筛选待审核队列（导航栏带待审核数量），可通过 / 驳回；驳回必须写原因，投稿人能看到 |
| 素材维护 | 管理员可增删改任意素材；学生可增删改自己未通过的稿子，改完自动重新进入待审核 |
| 附件 | 白名单格式（pdf/doc/docx/txt/md/图片），单文件不超过 10 MB |
| 权限 | 学生只看得到「已通过」的素材和自己的投稿；越权返回 403，不可见返回 404 |
| 后台管理 | `/admin/` 管理分类与素材，支持批量通过 / 驳回 |
| 测试 | 95 个用例，覆盖注册、登录、改资料、素材增删改查、投稿审核、可见性、权限与表单校验 |

## 技术栈

| 分类 | 选型 |
| --- | --- |
| 语言 | Python 3.8 ~ 3.13（已在 3.13 上实测通过） |
| 框架 | Django 4.1.12 |
| 数据库 | SQLite 3 |
| 模板 | Django Template Language |
| 样式 | 手写 CSS + 设计令牌（`static/css/tokens.css`、`app.css`）；无框架、无构建步骤 |
| 前端框架 | 无 |

> Django 4.1 已于 2023 年 12 月结束官方支持（EOL）。如需长期维护，建议升级到 4.2 LTS 或更高版本。

## 目录结构

```text
Django-Web/
├── SE/                     # 项目配置包（settings / urls / wsgi / asgi）
│   ├── settings.py
│   └── urls.py
├── user/                   # 用户应用：注册、登录、个人信息
│   ├── models.py           # Person 抽象基类 + Student / Administrator
│   ├── forms.py            # 登录、注册、修改表单 + 密码哈希 Mixin + 强度校验
│   ├── cbvs.py             # 基于类的视图（注册、修改）
│   ├── views.py            # 基于函数的视图（首页、登录、登出、分发）
│   ├── admin.py            # Django Admin 注册
│   ├── constants.py        # 账号长度、身份标识、权限提示等常量
│   ├── tests.py
│   ├── urls.py
│   └── migrations/
├── material/               # 素材应用
│   ├── models.py           # Category / Material（含审核状态）
│   ├── forms.py            # 素材表单 + 附件校验 + 审核表单
│   ├── views.py            # 列表、详情、新建、编辑、删除、审核 + 权限装饰器
│   ├── admin.py
│   ├── tests.py
│   ├── urls.py
│   └── migrations/
│       ├── 0001_initial.py
│       ├── 0002_seed_categories.py
│       └── 0003_material_review_workflow.py
├── templates/
│   ├── user/               # auth_base / login_home / login_detail / register / register_home / update
│   └── material/           # nav / list / detail / form / confirm_delete / review
├── static/
│   └── css/                # tokens.css（设计令牌）/ app.css（外壳与组件）
├── tools/                  # 前端自检脚本（对比度、结构）
├── media/                  # 用户上传的素材附件（不纳入版本控制）
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

> `db.sqlite3` 已从版本控制中移除（它是本地开发数据库，会随时变化）。首次运行**必须**先执行 `migrate`，否则会报 `no such table`。
>
> 迁移会一并完成两件事：把库里已有的**明文**密码批量转成哈希（原密码仍可登录），以及预置 5 个常用素材分类（诗词 / 文言文 / 现代文阅读 / 写作素材 / 名著导读）。

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

访问 <http://127.0.0.1:8000/admin/>，可以管理学生、管理员、素材分类与素材，并在素材列表上批量执行「标记为已通过 / 已驳回」。分类的增删改主要在这里完成。

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

共 95 个用例，覆盖注册编号分配、密码哈希与强度校验、两种身份的登录、资料修改、素材增删改查、投稿与审核状态流转、可见性控制、附件格式校验、搜索筛选与各级权限。

## 账号规则

- 账号 = **年级（4 位） + 编号（6 位）**，合计 **10 位**
- 示例：年级 `2023` + 编号 `000001` → 账号 `2023000001`
- 注册时只需填写年级，编号由系统取该年级当前最大编号 + 1 自动分配（该年级无记录时从 `000001` 开始）
- 同一身份下 `(年级, 编号)` 唯一；学生与管理员的编号各自独立递增
- 登录时按前 4 位解析年级、后 6 位解析编号，长度不等于 10 位会直接提示「账号必须为 10 位数」

## 页面与路由

| 路由 | 视图 | 权限 | 说明 |
| --- | --- | --- | --- |
| `/` | `user.views.home` | 公开 | 首页，选择身份（路由名 `index`） |
| `/user/login/` | `user.views.home` | 公开 | 与首页相同（路由名 `login`） |
| `/user/login/<kind>` | `user.views.login` | 公开 | 登录（路由名 `login_detail`） |
| `/user/logout/` | `user.views.logout` | 已登录 | 退出登录 |
| `/user/register/` | `user.views.register_home` | 公开 | 注册身份选择页（路由名 `register`） |
| `/user/register/<kind>` | `user.views.register` | 公开 | 注册（路由名 `register_detail`） |
| `/user/update/<kind>` | `user.views.update` | 已登录 | 修改个人信息 |
| `/material/<kind>/` | `material.views.home` | 已登录 | 素材列表（分类 / 关键词 / 状态筛选） |
| `/material/<kind>/detail/<pk>` | `material.views.detail` | 已登录 | 素材详情 |
| `/material/<kind>/create` | `material.views.create` | 已登录 | 新建素材（管理员直接发布，学生投稿转待审核） |
| `/material/<kind>/edit/<pk>` | `material.views.edit` | 管理员 / 作者本人 | 编辑素材 |
| `/material/<kind>/delete/<pk>` | `material.views.delete` | 管理员 / 作者本人 | 删除素材（GET 确认，POST 执行） |
| `/material/<kind>/review/<pk>` | `material.views.review` | 仅管理员 | 审核素材（通过 / 驳回） |
| `/admin/` | Django Admin | 超级用户 | 后台管理 |

`kind` 只接受 `student` 与 `administrator`，其余值返回 **400**；身份不足返回 **403**；未登录则跳回对应身份的登录页；看不到的资源返回 **404**。

## 素材库

### 权限

| 操作 | 学生 | 管理员 |
| --- | --- | --- |
| 浏览列表 / 搜索 / 筛选 | 已通过的素材 + 自己的投稿 | 全部（可按状态筛选） |
| 查看详情、下载附件 | 同上，看不到的直接 404 | 全部 |
| 新建（投稿） | ✅ 进入「待审核」 | ✅ 直接「已通过」 |
| 编辑 / 删除 | 只能改自己「待审核 / 已驳回」的稿子 | 任意素材 |
| 审核（通过 / 驳回） | ❌ 403 | ✅ |

权限由 `material/views.py` 里的 `require_person()` 装饰器统一处理：它先校验 `kind` 合法、再确认已登录，可选地再要求管理员身份，通过后把当前用户挂到 `request.person`。而「能不能改这一条素材」由 `can_manage()` 判断，因为那要拿到具体对象才知道。

### 投稿与审核

素材有 `pending` / `approved` / `rejected` 三种状态，流转规则：

```text
管理员录入 ──────────────────────────────→ 已通过
                                            ↑
学生投稿 → 待审核 ──审核通过───────────────┘
             ↑  ↑
             │  └──审核驳回（必须写原因）──→ 已驳回
             │                                │
             └────────── 作者改稿后重投 ───────┘
```

- 学生**只能看到「已通过」的素材，加上自己投的全部稿件**，看不到别人没通过审核的稿子
- 学生改自己「待审核 / 已驳回」的稿子后，状态回到「待审核」，上一次的审核意见会被清空
- 一旦通过，作者就不能再自己修改已发布的内容（返回 403），需要联系管理员
- 管理员在导航栏能看到「待审核 (N)」的数量提示，也可以直接把 `/material/administrator/?status=pending` 当审核队列用

### 附件

- 允许格式：`pdf` `doc` `docx` `txt` `md` `jpg` `jpeg` `png` `gif` `webp`
- 单文件上限 10 MB
- 存储位置：`media/materials/<年>/<月>/`，该目录已加入 `.gitignore`

### 分类

迁移会预置 5 个常用分类。新增或调整分类请到 `/admin/material/category/`。分类被素材引用时不允许删除（外键为 `PROTECT`）。

## 界面设计

本版界面重塑使用 `frontend-design-3` 技能完成（ClawHub），方向定为 **「纸本」——浅色印刷 / 书刊**。

> 与 `main` 分支上那版（`website-ui-designer` 的 bold-creative：深色霓虹 + 侧栏应用外壳）是**同一套视图与模板的两套版式方案**，供对照选择，功能与测试完全一致。

### 视觉方向

| 项 | 取值 |
| --- | --- |
| 底色 | `#F2ECE0` 宣纸米 —— 不用纯白，纯白在整屏阅读时刺眼且没有纸感 |
| 主色 | `#A32E22` 朱砂 —— 既是主操作色，也是「批红」与印章的颜色 |
| 副色 | `#1F4B5E` 靛青 —— 链接与信息提示 |
| 语义色 | 赭石（待审核）、松绿（已通过）、朱深（危险），全部低饱和 |
| 字体 | 宋体（显示与正文）、楷体（引用与印章）、黑体（UI 骨架）；**全部走系统字库，不引外链字体** |
| 动效 | 刊头规则先「画」出来，内容再依次落下；印章有一处落印微动效，全部尊重 `prefers-reduced-motion` |

**方向选择的理由**：这套系统的内容本身就是中文文学素材（诗词、文言文、现代文阅读）。印刷品的字体与版式语言是这个题材的天然表达，也让它一眼区别于通用的后台管理模板。

### 签名元素只有两个，都很克制

1. **钤印式状态方章** —— 状态不写成彩色小标签，而是一枚描边方章（待审核 / 已通过 / 已驳回），方形小圆角、略作倾斜，像盖上去的印。状态同时带文字，不只靠颜色表达。
2. **主数字着朱砂** —— 统计栏的主数字是全站唯一使用主色的数字。

### 版式结构（与 main 分支的主要差异）

| | main（v1 bold-creative） | 本分支（v2 纸本） |
| --- | --- | --- |
| 导航 | 固定侧栏 240px + 顶栏的应用外壳 | 双规则**刊头** + 目录式编号导航（01 / 02 / 03） |
| 列表 | 通用数据表格 | **账页式**目录：序号列 + 宋体大标题 + 加宽字距的表头 |
| 统计 | 顶部 KPI 卡片行 | 移到**页边批注栏**（marginalia），按账本栏目数字排布 |
| 圆角 | 胶囊（最大到 999px） | 印刷方角（1–5px） |
| 阴影 | 卡片浮起的大投影 | 纸叠纸：1px 硬阴影 + 发丝线 |
| 登录页 | 深色品牌板 + 表单卡 | **墨面 + 纸面斜切咬合**，墨面上有稿纸格 |
| 正文 | 无衬线 | 详情页正文按「引文」处理：楷体 + 朱砂边线 |

### 令牌分三层

`static/css/tokens.css` 按 primitive → semantic → component 三层组织，组件样式只引用后两层：

1. **primitive**：原始色阶（纸 / 墨 / 五种颜料）、间距刻度、字号、动效曲线 —— 全项目唯一允许出现裸色值的地方
2. **semantic**：`--bg` / `--text` / `--accent` / `--warn` … 语义令牌名与 main 分支**完全一致**，两版可以直接逐项对照
3. **component**：字体栈、版心宽度、发丝线细则、动效时长

`static/css/app.css` 里**不含任何裸色值**（有校验脚本把关）。整份样式表里朱砂只出现一次，就在 tokens.css 的 primitive 层。

### 无障碍

每页一个 `h1`、表头带 `scope`、表单控件都有 `label` 关联、状态不只靠颜色、保留可见焦点环、所有页面都有「跳到主要内容」与 `main` landmark。焦点环放在令牌层，全站只有一个来源。

### 重新校验

```bash
# 配色对比度（31 项，含半透明浅底按合成后颜色计算）
python tools/check_tokens_contrast.py static/css/tokens.css

# CSS 规则 + 实际渲染出的 HTML 结构（119 项）
# 需先把页面抓成本地 html，见脚本头部说明
python tools/check_frontend.py . <抓取目录>
```

> 两项**无法程序化验证**、本次也未验证的内容：各断点下的真实视觉观感、是否出现元素重叠。脚本能覆盖结构与规则，覆盖不了「好不好看」。本机浏览器截图一律超出工具的体积上限（`clip` 裁剪也绕不过去），所以这一步需要你在浏览器里按 360 / 768 / 1280 / 1600 宽度人工过一遍。


## 数据模型

### user 应用

`Person` 是抽象基类，`Student` 与 `Administrator` 继承它，只覆盖 `number` 字段的中文名与各自的唯一约束名。

公共能力：`get_id()` 返回 10 位账号；`set_password(raw)` 生成 PBKDF2-SHA256 哈希；`check_password(raw)` 做恒定时间校验。

| 字段 | 类型 | verbose_name | 说明 |
| --- | --- | --- | --- |
| `name` | `CharField(50)` | 姓名 | |
| `gender` | `CharField(10)` | 性别 | `m` 男 / `f` 女，默认 `m` |
| `birthday` | `DateField` | 生日 | |
| `email` | `EmailField` | 邮箱 | |
| `info` | `CharField(255)` | 个人简介 | |
| `grade` | `CharField(4)` | 年级 | 注册后不可修改 |
| `number` | `CharField(6)` | 学号 / 编号 | 注册时自动分配，不可修改 |
| `password` | `CharField(128)` | 密码 | 存放哈希，不是明文 |

### material 应用

**Category**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | `CharField(50)` | 分类名称，唯一 |
| `description` | `CharField(255)` | 分类说明，可空 |
| `order` | `PositiveSmallIntegerField` | 排序，越小越靠前 |

**Material**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | `CharField(100)` | 标题 |
| `category` | `ForeignKey(Category, PROTECT)` | 分类，被引用时不可删除 |
| `source` | `CharField(100)` | 出处 / 作者，可空 |
| `body` | `TextField` | 正文 |
| `attachment` | `FileField` | 可选附件，上传到 `materials/%Y/%m/` |
| `status` | `CharField(20)` | `pending` 待审核 / `approved` 已通过 / `rejected` 已驳回 |
| `review_comment` | `CharField(255)` | 审核意见，驳回时必填 |
| `reviewed_at` | `DateTimeField` | 审核时间，可空 |
| `created_by` | `ForeignKey(Administrator, SET_NULL)` | 管理员录入人；与学生投稿互斥 |
| `submitted_by` | `ForeignKey(Student, SET_NULL)` | 投稿学生；与管理员录入互斥 |
| `created_at` / `updated_at` | `DateTimeField` | 自动维护 |

`created_by` 与 `submitted_by` **至多只有一个非空**，由 `CheckConstraint(material_at_most_one_author)` 在数据库层保证。

这里没有用 contenttypes 的泛型外键：`Student` 与 `Administrator` 本就是两张表，拆成两个可空外键既保留了真正的外键约束，读写也更直观。模型上提供了 `author` / `author_kind` / `author_name` / `author_uid` / `is_owned_by()` 几个属性来屏蔽这个差异。

## 修复记录

以下缺陷已在 2026-10 的一次集中修复中处理完毕，测试用例覆盖了每一条。

| 优先级 | 位置 | 问题 | 处理方式 |
| --- | --- | --- | --- |
| 高 | `material/views.py` | 身份白名单写成 `["student", "teacher"]`，管理员登录后被判为非法身份，无限重定向回登录页 | 改用统一的 `KINDS` 常量 |
| 高 | `material/views.py` | 查询用了不存在的字段 `department_no`，会抛 `FieldError` | 改为按 `grade` + `number` 查询 |
| 高 | `user/forms.py` + `user/views.py` | 管理员登录表单字段名为 `aid`，视图却统一读 `cleaned_data["uid"]`，管理员登录直接 `KeyError` | 两个登录表单统一使用 `uid` |
| 高 | `user/forms.py` | 两个注册表单的 `clean()` 被写在 `class Meta` 内部，确认密码校验从未执行；`AdmRegisterForm.clean` 还错误引用了 `StuRegisterForm` | 校验逻辑上移到 `PersonRegisterForm` 表单类层级 |
| 高 | `user/cbvs.py` | `CreateAdministratorView` 用 `Student` 表计算下一个编号，管理员编号会与学生撞号 | 编号分配改为基于 `self.model` |
| 中 | 全局 | 密码以明文存储与比对 | 改为 `make_password` / `check_password`，并提供数据迁移转换历史数据 |
| 中 | `SE/settings.py` | `SECRET_KEY` 硬编码进仓库、`DEBUG=True` 硬编码 | 三者全部改为从环境变量读取 |
| 中 | `user/views.py` | `from audioop import reverse` —— `audioop` 已在 Python 3.13 中移除，项目无法在 3.13 上启动 | 删除，改用 `django.urls.reverse` |
| 中 | `user/forms.py` | `AdmRegisterForm` 未声明 `password` 字段，ModelForm 把它渲染成明文输入框 | 在基类中统一声明为 `PasswordInput` |
| 中 | `templates/user/login_detail.html` | 块名写成 `welcome-message`，与父模板的 `welcome_message` 不匹配，注册成功提示从未渲染 | 改为 `welcome_message` |
| 中 | `user/cbvs.py` | 管理员的修改表单沿用了注册表单，年级可改 —— 而年级参与账号拼接，改完账号就变了 | 新增 `AdmUpdateForm`，收起年级 |
| 低 | 多处 | 无用 import：`multiprocessing.context`、`pydoc.cram`、`is_valid_path`、`decimal.MAX_EMAX`、`dataclasses.fields`、`random` 等 | 全部清理 |
| 低 | `SE/urls.py` + `user/urls.py` | 两处 urlconf 都定义了名为 `login` 的路由，反向解析靠参数个数区分，含义含糊 | 首页改名 `index`，带身份的路由改名 `login_detail` / `register_detail` |
| 低 | `SE/urls.py` | `import admin` 却没挂路由，`/admin/` 一直是 404 | 补上 `path("admin/", admin.site.urls)` |
| 低 | `user/admin.py` | 后台未注册任何模型 | 注册 `Student` / `Administrator`，并从后台表单排除密码字段 |
| 低 | `material/views.py` | `student_home` 与 `administrator_home` 两份完全重复的代码 | 合并为单个 `home` 视图 |
| 低 | `user/tests.py`、`material/tests.py` | 仍是 Django 默认空模板，没有测试覆盖 | 补充测试用例 |
| 低 | `SE/settings.py` | `LANGUAGE_CODE='en-us'` / `TIME_ZONE='UTC'`，与全中文界面不一致 | 改为 `zh-hans` / `Asia/Shanghai` |
| 低 | `templates/user/update.html` | 重复 `{% load static %}` 与重复 `<link>`；标题误写成 “Register” | 清理并改为「修改个人信息」 |

## 后续可做

- **分类的界面化管理**：目前分类的增删改走 Django Admin，可以补一套管理员页面
- **分页**：素材列表一次性全量渲染，数据量大后需要分页
- **审核通知**：稿件被通过 / 驳回后目前只在页面上可见，可以加站内消息或邮件提醒
- **注册并发**：编号分配是「查最大值 + 1」，并发注册同一届时会撞唯一约束，可改用重试或数据库序列
- **附件安全**：目前只校验扩展名，生产环境还应校验真实 MIME 类型、做病毒扫描，并限制单用户配额
- **升级 Django**：4.1 已 EOL，建议升到 4.2 LTS
- **补 CI**：加上 GitHub Actions 跑 `manage.py test`

## 安全说明

本项目定位为**教学 / 课程作业**，请勿直接部署到生产环境。

**已处理**

1. 密码经 PBKDF2-SHA256 哈希存储，不再保存明文
2. 新设密码会经过强度校验（长度 ≥ 8、非纯数字、非常见密码、与邮箱不过于相似）
3. `SECRET_KEY` / `DEBUG` / `ALLOWED_HOSTS` 从环境变量读取
4. 退出登录使用 `session.flush()`，清空数据并轮换 session key
5. 素材的增删改与审核都做了服务端权限校验，不只是隐藏按钮
6. 学生看不到别人未通过审核的稿件，且返回 404 而不是 403，避免探测出记录是否存在
7. 附件做了扩展名与体积白名单校验

**仍需注意**

1. 调试模式默认开启，线上务必设置 `DJANGO_DEBUG=0`
2. 附件仅校验扩展名，未校验真实文件类型，也未做病毒扫描
3. 登录接口没有限流，可被暴力尝试
4. 开发环境下附件由 Django 直接托管，生产环境应交给 Nginx 等静态服务器
5. 早期提交历史里的 `SECRET_KEY` 已经泄漏，如曾有线上部署请务必更换

## License

本项目基于 [MIT License](LICENSE) 开源。
