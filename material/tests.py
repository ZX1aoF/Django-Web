"""material 应用的回归测试。"""

import shutil
import tempfile
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from material.models import Category, Material
from material.views import PAGE_SIZE, get_user
from user.models import Administrator, Student

RAW_PASSWORD = "s3cret-pass"


def make_student(grade="2023", number="000001"):
    student = Student(
        name="张三",
        gender="m",
        birthday=date(2000, 1, 1),
        email="student@example.com",
        info="简介",
        grade=grade,
        number=number,
    )
    student.set_password(RAW_PASSWORD)
    student.save()
    return student


def make_administrator(grade="2022", number="000001"):
    administrator = Administrator(
        name="管理员",
        gender="f",
        birthday=date(1980, 5, 20),
        email="admin@example.com",
        info="管理端账号",
        grade=grade,
        number=number,
    )
    administrator.set_password(RAW_PASSWORD)
    administrator.save()
    return administrator


class MaterialViewTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.administrator = make_administrator()

    def login(self, kind, uid):
        return self.client.post(
            reverse("login_detail", args=[kind]), {"uid": uid, "password": RAW_PASSWORD}
        )

    def test_anonymous_visitor_is_redirected_to_login(self):
        response = self.client.get(reverse("material", args=["student"]))
        self.assertRedirects(response, reverse("login_detail", args=["student"]))

    def test_student_can_open_the_student_page(self):
        self.login("student", self.student.get_id())
        response = self.client.get(reverse("material", args=["student"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "学生端")

    def test_administrator_can_open_the_administrator_page(self):
        # 回归：get_user 的身份白名单曾写成 ["student", "teacher"]，
        # 管理员登录后会被判定为非法身份，一直被打回登录页
        self.login("administrator", self.administrator.get_id())
        response = self.client.get(reverse("material", args=["administrator"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "管理员端")

    def test_session_kind_must_match_the_requested_kind(self):
        self.login("student", self.student.get_id())
        response = self.client.get(reverse("material", args=["administrator"]))
        self.assertRedirects(response, reverse("login_detail", args=["administrator"]))

    def test_invalid_kind_returns_400(self):
        response = self.client.get(reverse("material", args=["teacher"]))
        self.assertEqual(response.status_code, 400)


class GetUserTests(TestCase):
    def setUp(self):
        self.administrator = make_administrator()

    def request_with_session(self, session):
        request = RequestFactory().get("/material/")
        request.session = session
        return request

    def test_returns_none_when_not_logged_in(self):
        request = self.request_with_session({})
        self.assertIsNone(get_user(request, "student"))

    def test_returns_none_for_stale_uid(self):
        # 账号在数据库里被改动后 session 里的 uid 会失配，此时应返回 None 而不是抛异常
        request = self.request_with_session({"kind": "student", "user": "2023999999"})
        self.assertIsNone(get_user(request, "student"))

    def test_administrator_lookup_uses_the_grade_field(self):
        # 回归：旧代码查的是不存在的 department_no 字段，会直接抛 FieldError
        request = self.request_with_session(
            {"kind": "administrator", "user": self.administrator.get_id()}
        )
        user = get_user(request, "administrator")
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.administrator.pk)

    def test_returns_none_for_invalid_kind(self):
        request = self.request_with_session({"kind": "teacher", "user": "2022000001"})
        self.assertIsNone(get_user(request, "teacher"))


class MaterialListViewTests(TestCase):
    """素材列表：访问控制、搜索与分类筛选。"""

    def setUp(self):
        self.student = make_student()
        self.administrator = make_administrator()
        # 分类名不要用迁移里预置的那几个，否则会撞 unique 约束
        self.category = Category.objects.create(
            name="测试分类甲", description="测试用分类", order=10
        )
        self.other_category = Category.objects.create(name="测试分类乙", order=20)
        self.material = Material.objects.create(
            title="静夜思",
            category=self.category,
            source="李白",
            body="床前明月光，疑是地上霜。",
            created_by=self.administrator,
        )

    def login(self, kind, uid):
        return self.client.post(
            reverse("login_detail", args=[kind]), {"uid": uid, "password": RAW_PASSWORD}
        )

    def login_student(self):
        return self.login("student", self.student.get_id())

    def login_administrator(self):
        return self.login("administrator", self.administrator.get_id())

    def test_list_requires_login(self):
        response = self.client.get(reverse("material", args=["student"]))
        self.assertRedirects(response, reverse("login_detail", args=["student"]))

    def test_student_sees_materials_but_no_create_entry(self):
        self.login_student()
        response = self.client.get(reverse("material", args=["student"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "静夜思")
        self.assertNotContains(response, "新建素材")

    def test_administrator_sees_create_entry(self):
        self.login_administrator()
        response = self.client.get(reverse("material", args=["administrator"]))
        self.assertContains(response, "新建素材")

    def test_search_matches_title(self):
        Material.objects.create(title="春晓", category=self.category, body="春眠不觉晓")
        self.login_student()

        response = self.client.get(reverse("material", args=["student"]), {"q": "春晓"})
        self.assertContains(response, "春晓")
        self.assertNotContains(response, "静夜思")

    def test_search_matches_body(self):
        Material.objects.create(title="春晓", category=self.category, body="春眠不觉晓")
        self.login_student()

        response = self.client.get(reverse("material", args=["student"]), {"q": "明月光"})
        self.assertContains(response, "静夜思")
        self.assertNotContains(response, "春晓")

    def test_filter_by_category(self):
        Material.objects.create(
            title="陋室铭", category=self.other_category, body="山不在高"
        )
        self.login_student()

        response = self.client.get(
            reverse("material", args=["student"]), {"category": self.other_category.pk}
        )
        self.assertContains(response, "陋室铭")
        self.assertNotContains(response, "静夜思")

    def test_non_numeric_category_is_ignored(self):
        self.login_student()
        response = self.client.get(reverse("material", args=["student"]), {"category": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "静夜思")

    def test_empty_library_shows_placeholder(self):
        Material.objects.all().delete()
        self.login_student()
        response = self.client.get(reverse("material", args=["student"]))
        self.assertContains(response, "素材库还是空的")


class MaterialCatalogTests(TestCase):
    """列表页的「目录」能力：结果计数、排序、分页、分面计数、筛选标签。

    这几件是图书馆目录（OPAC）类站点的标准配置，本版按参考资料补齐。
    """

    def setUp(self):
        self.administrator = make_administrator()
        self.category = Category.objects.create(name="目录测试甲", order=10)
        self.other_category = Category.objects.create(name="目录测试乙", order=20)
        self.url = reverse("material", args=["administrator"])
        self.client.post(
            reverse("login_detail", args=["administrator"]),
            {"uid": self.administrator.get_id(), "password": RAW_PASSWORD},
        )

    def make(self, title, category=None, days_ago=0):
        material = Material.objects.create(
            title=title,
            category=category or self.category,
            body="正文",
            created_by=self.administrator,
        )
        if days_ago:
            # updated_at 是 auto_now，只能用 update() 绕过去造时间差
            Material.objects.filter(pk=material.pk).update(
                updated_at=timezone.now() - timedelta(days=days_ago)
            )
        return material

    def test_total_count_is_shown(self):
        self.make("甲")
        self.make("乙")
        response = self.client.get(self.url)
        self.assertContains(response, "共 <strong>2</strong> 篇")

    def test_filtered_view_says_so(self):
        self.make("甲")
        self.make("乙")
        response = self.client.get(self.url, {"q": "甲"})
        self.assertContains(response, "共 <strong>1</strong> 篇")
        self.assertContains(response, "（已筛选）")

    def test_default_sort_is_newest_first(self):
        # 单字码点：乙(U+4E59) < 甲(U+7532)，所以标题升序与时间倒序的结果相反
        self.make("乙素材", days_ago=5)
        self.make("甲素材", days_ago=0)

        content = self.client.get(self.url).content.decode()
        self.assertLess(content.index("甲素材"), content.index("乙素材"))

    def test_sort_by_title(self):
        self.make("乙素材", days_ago=5)
        self.make("甲素材", days_ago=0)

        content = self.client.get(self.url, {"sort": "title"}).content.decode()
        self.assertLess(content.index("乙素材"), content.index("甲素材"))

    def test_unknown_sort_falls_back_to_default(self):
        self.make("乙素材", days_ago=5)
        self.make("甲素材", days_ago=0)

        content = self.client.get(self.url, {"sort": "not-a-sort"}).content.decode()
        self.assertLess(content.index("甲素材"), content.index("乙素材"))

    def test_sort_control_renders_every_option(self):
        response = self.client.get(self.url)
        for label in ("最近更新", "最早更新", "标题"):
            self.assertContains(response, label)

    def test_pagination_splits_the_list(self):
        for index in range(PAGE_SIZE + 3):
            self.make("素材%03d" % index)

        first = self.client.get(self.url)
        self.assertEqual(first.context["page_obj"].number, 1)
        self.assertEqual(first.context["total_count"], PAGE_SIZE + 3)
        self.assertEqual(len(first.context["materials"]), PAGE_SIZE)
        self.assertContains(first, "第 1 / 2 页")

        second = self.client.get(self.url, {"page": 2})
        self.assertEqual(second.context["page_obj"].number, 2)
        self.assertEqual(len(second.context["materials"]), 3)

    def test_out_of_range_page_falls_back_to_the_last_one(self):
        for index in range(PAGE_SIZE + 1):
            self.make("素材%03d" % index)

        response = self.client.get(self.url, {"page": 999})
        self.assertEqual(response.context["page_obj"].number, 2)

    def test_pager_links_keep_the_active_filters(self):
        for index in range(PAGE_SIZE + 1):
            self.make("needle %02d" % index)

        response = self.client.get(self.url, {"q": "needle"})
        self.assertContains(response, 'href="?q=needle&amp;page=2"')

    def test_category_facet_shows_counts(self):
        self.make("甲", category=self.category)
        self.make("乙", category=self.category)
        self.make("丙", category=self.other_category)

        response = self.client.get(self.url)
        self.assertContains(response, "目录测试甲（2）")
        self.assertContains(response, "目录测试乙（1）")

    def test_category_facet_ignores_the_category_filter_itself(self):
        """选中某分类后，其他分类的计数必须还在，否则分面等于废掉。"""
        self.make("甲", category=self.category)
        self.make("乙", category=self.other_category)

        response = self.client.get(self.url, {"category": self.other_category.pk})
        self.assertContains(response, "目录测试甲（1）")
        self.assertContains(response, "目录测试乙（1）")

    def test_active_filters_render_removable_chips(self):
        self.make("abc")
        response = self.client.get(
            self.url, {"q": "abc", "category": self.category.pk}
        )

        self.assertContains(response, "当前条件")
        self.assertContains(response, "关键词：abc")
        self.assertContains(response, "分类：目录测试甲")
        # 分类那个「×」只去掉 category，保留关键词
        self.assertContains(response, 'href="%s?q=abc"' % self.url)
        # 关键词那个「×」只去掉 q，保留分类
        self.assertContains(response, 'href="%s?category=%d"' % (self.url, self.category.pk))

    def test_no_chips_when_nothing_is_filtered(self):
        self.make("abc")
        response = self.client.get(self.url)
        self.assertNotContains(response, "当前条件")


class FormErrorSummaryTests(TestCase):
    """提交失败时的错误摘要（参考 GOV.UK Design System 的 Error summary）。"""

    def setUp(self):
        self.administrator = make_administrator()
        self.client.post(
            reverse("login_detail", args=["administrator"]),
            {"uid": self.administrator.get_id(), "password": RAW_PASSWORD},
        )
        self.empty_post = {"title": "", "category": "", "source": "", "body": ""}

    def test_summary_lists_errors_and_links_to_the_fields(self):
        response = self.client.post(
            reverse("material_create", args=["administrator"]), self.empty_post
        )
        # 断言真实元素，而不是 "error-summary" 这个子串 ——
        # 渐进增强脚本里的 data-error-summary 选择器也含这个子串
        self.assertContains(response, 'class="error-summary')
        self.assertContains(response, "处需要修改")
        self.assertContains(response, 'href="#id_title"')
        self.assertContains(response, 'href="#id_category"')

    def test_summary_keeps_the_field_level_errors_too(self):
        response = self.client.post(
            reverse("material_create", args=["administrator"]), self.empty_post
        )
        # 两种提示都要有：摘要在页面顶部，字段旁的提示在字段下方
        self.assertContains(response, "errorlist")

    def test_page_title_is_prefixed_for_screen_readers(self):
        response = self.client.post(
            reverse("material_create", args=["administrator"]), self.empty_post
        )
        self.assertContains(response, "<title>Error: ")

    def test_no_summary_when_the_form_is_clean(self):
        response = self.client.get(reverse("material_create", args=["administrator"]))
        self.assertNotContains(response, 'class="error-summary')


class MaterialDetailTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.category = Category.objects.create(name="测试分类甲", order=10)
        self.material = Material.objects.create(
            title="静夜思", category=self.category, source="李白", body="床前明月光，疑是地上霜。"
        )
        self.client.post(
            reverse("login_detail", args=["student"]),
            {"uid": self.student.get_id(), "password": RAW_PASSWORD},
        )

    def test_student_can_read_detail(self):
        response = self.client.get(
            reverse("material_detail", args=["student", self.material.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "床前明月光")
        self.assertContains(response, "李白")

    def test_detail_has_no_edit_entry_for_student(self):
        response = self.client.get(
            reverse("material_detail", args=["student", self.material.pk])
        )
        self.assertNotContains(response, "编辑")

    def test_missing_material_returns_404(self):
        response = self.client.get(reverse("material_detail", args=["student", 9999]))
        self.assertEqual(response.status_code, 404)


class MaterialPermissionTests(TestCase):
    """学生不能改动不属于自己的素材。"""

    def setUp(self):
        self.student = make_student()
        self.administrator = make_administrator()
        self.category = Category.objects.create(name="测试分类甲", order=10)
        self.material = Material.objects.create(
            title="静夜思", category=self.category, body="床前明月光"
        )
        self.client.post(
            reverse("login_detail", args=["student"]),
            {"uid": self.student.get_id(), "password": RAW_PASSWORD},
        )

    def test_student_submission_is_not_published_directly(self):
        # 投稿入口对学生开放，但提交后是「待审核」，不会直接进公共素材库
        response = self.client.post(
            reverse("material_create", args=["student"]),
            {
                "title": "学生投稿",
                "category": self.category.pk,
                "source": "",
                "body": "床前明月光",
            },
        )
        material = Material.objects.get(title="学生投稿")

        self.assertRedirects(
            response, reverse("material_detail", args=["student", material.pk])
        )
        self.assertEqual(material.status, Material.Status.PENDING)
        self.assertEqual(material.submitted_by, self.student)

    def test_student_cannot_open_edit_page(self):
        response = self.client.get(reverse("material_edit", args=["student", self.material.pk]))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_delete(self):
        response = self.client.post(
            reverse("material_delete", args=["student", self.material.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Material.objects.filter(pk=self.material.pk).exists())

    def test_student_session_cannot_be_used_on_administrator_paths(self):
        # 用学生的 session 去访问管理员路径，会被身份校验挡回管理员登录页
        response = self.client.get(reverse("material_create", args=["administrator"]))
        self.assertRedirects(response, reverse("login_detail", args=["administrator"]))

    def test_invalid_kind_returns_400(self):
        response = self.client.get(reverse("material", args=["teacher"]))
        self.assertEqual(response.status_code, 400)


class MaterialCrudTests(TestCase):
    """管理员对素材的增删改查。"""

    def setUp(self):
        self.administrator = make_administrator()
        self.category = Category.objects.create(name="测试分类甲", order=10)
        self.client.post(
            reverse("login_detail", args=["administrator"]),
            {"uid": self.administrator.get_id(), "password": RAW_PASSWORD},
        )

    def payload(self, **overrides):
        data = {
            "title": "静夜思",
            "category": self.category.pk,
            "source": "李白",
            "body": "床前明月光，疑是地上霜。",
        }
        data.update(overrides)
        return data

    def test_administrator_can_create_material(self):
        response = self.client.post(
            reverse("material_create", args=["administrator"]), self.payload()
        )
        material = Material.objects.get()

        self.assertRedirects(
            response, reverse("material_detail", args=["administrator", material.pk])
        )
        self.assertEqual(material.title, "静夜思")
        # 录入人应自动记为当前登录的管理员
        self.assertEqual(material.created_by, self.administrator)

    def test_create_shows_success_message(self):
        response = self.client.post(
            reverse("material_create", args=["administrator"]), self.payload(), follow=True
        )
        self.assertContains(response, "已创建")

    def test_category_is_required(self):
        response = self.client.post(
            reverse("material_create", args=["administrator"]), self.payload(category="")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Material.objects.count(), 0)
        self.assertIn("category", response.context["form"].errors)

    def test_title_is_required(self):
        response = self.client.post(
            reverse("material_create", args=["administrator"]), self.payload(title="")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Material.objects.count(), 0)
        self.assertIn("title", response.context["form"].errors)

    def test_administrator_can_edit_material(self):
        material = Material.objects.create(
            title="静夜思", category=self.category, source="李白", body="旧正文"
        )
        response = self.client.post(
            reverse("material_edit", args=["administrator", material.pk]),
            self.payload(body="举头望明月，低头思故乡。"),
        )

        self.assertRedirects(
            response, reverse("material_detail", args=["administrator", material.pk])
        )
        material.refresh_from_db()
        self.assertIn("举头望明月", material.body)

    def test_delete_needs_post_confirmation(self):
        material = Material.objects.create(
            title="静夜思", category=self.category, body="床前明月光"
        )

        # GET 只展示确认页，不删除
        response = self.client.get(
            reverse("material_delete", args=["administrator", material.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "确认删除")
        self.assertTrue(Material.objects.filter(pk=material.pk).exists())

        # POST 才真正删除
        response = self.client.post(
            reverse("material_delete", args=["administrator", material.pk])
        )
        self.assertRedirects(response, reverse("material", args=["administrator"]))
        self.assertFalse(Material.objects.filter(pk=material.pk).exists())

    def test_category_in_use_cannot_be_deleted(self):
        Material.objects.create(title="静夜思", category=self.category, body="x")
        with self.assertRaises(ProtectedError):
            self.category.delete()


class MaterialAttachmentTests(TestCase):
    """附件上传：扩展名白名单。"""

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=self.media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        self.administrator = make_administrator()
        self.category = Category.objects.create(name="测试分类甲", order=10)
        self.client.post(
            reverse("login_detail", args=["administrator"]),
            {"uid": self.administrator.get_id(), "password": RAW_PASSWORD},
        )

    def payload(self, attachment):
        return {
            "title": "静夜思",
            "category": self.category.pk,
            "source": "李白",
            "body": "床前明月光",
            "attachment": attachment,
        }

    def test_allowed_extension_is_accepted(self):
        upload = SimpleUploadedFile("静夜思.txt", "床前明月光".encode("utf-8"))
        self.client.post(
            reverse("material_create", args=["administrator"]), self.payload(upload)
        )

        self.assertEqual(Material.objects.count(), 1)
        self.assertTrue(Material.objects.get().attachment.name.endswith(".txt"))

    def test_disallowed_extension_is_rejected(self):
        upload = SimpleUploadedFile("payload.exe", b"MZ")
        response = self.client.post(
            reverse("material_create", args=["administrator"]), self.payload(upload)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Material.objects.count(), 0)
        self.assertIn("attachment", response.context["form"].errors)

    def test_creating_without_attachment_is_allowed(self):
        payload = self.payload(None)
        del payload["attachment"]
        self.client.post(reverse("material_create", args=["administrator"]), payload)

        self.assertEqual(Material.objects.count(), 1)
        self.assertFalse(Material.objects.get().attachment)


class MaterialAuthorConstraintTests(TestCase):
    def test_material_cannot_have_two_authors(self):
        # created_by 与 submitted_by 至多只有一个非空，由 CheckConstraint 兜底
        category = Category.objects.create(name="测试分类甲", order=10)
        administrator = make_administrator()
        student = make_student()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Material.objects.create(
                    title="两个作者",
                    category=category,
                    body="正文",
                    created_by=administrator,
                    submitted_by=student,
                )


class StudentSubmissionTests(TestCase):
    """学生投稿：默认待审核，只有自己和管理员看得到。"""

    def setUp(self):
        self.student = make_student()
        self.other_student = make_student(number="000002")
        self.administrator = make_administrator()
        self.category = Category.objects.create(name="测试分类甲", order=10)

    def login(self, kind, uid):
        return self.client.post(
            reverse("login_detail", args=[kind]), {"uid": uid, "password": RAW_PASSWORD}
        )

    def payload(self, **overrides):
        data = {
            "title": "我的投稿",
            "category": self.category.pk,
            "source": "佚名",
            "body": "床前明月光，疑是地上霜。",
        }
        data.update(overrides)
        return data

    def submit(self, student, **overrides):
        """以指定学生身份投稿。

        follow=True 是必要的：投稿成功后会往 messages 里塞一条带标题的提示，
        如果不跟随跳转把它渲染掉，这条消息会残留到下一个请求里，
        让后续的 assertNotContains 误判标题还在页面上。
        """
        self.login("student", student.get_id())
        return self.client.post(
            reverse("material_create", args=["student"]),
            self.payload(**overrides),
            follow=True,
        )

    def test_student_can_open_the_submit_page(self):
        self.login("student", self.student.get_id())
        response = self.client.get(reverse("material_create", args=["student"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "投稿素材")
        self.assertContains(response, "需要管理员审核")

    def test_submission_is_pending_and_attributed_to_the_student(self):
        self.submit(self.student)
        material = Material.objects.get()

        self.assertEqual(material.status, Material.Status.PENDING)
        self.assertEqual(material.submitted_by, self.student)
        self.assertIsNone(material.created_by)
        self.assertEqual(material.author_kind, "student")
        self.assertEqual(material.author_name, self.student.name)
        self.assertEqual(material.author_uid, self.student.get_id())

    def test_submission_lands_on_detail_with_pending_notice(self):
        response = self.submit(self.student)

        # 一次跳转，最终停在详情页
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 302)
        self.assertContains(response, "通过之后其他同学才能看到")
        self.assertContains(response, "提交人")

    def test_owner_sees_own_pending_submission_in_the_list(self):
        self.submit(self.student, title="未审核的稿子")
        response = self.client.get(reverse("material", args=["student"]))

        self.assertContains(response, "未审核的稿子")

    def test_other_students_cannot_see_pending_submissions(self):
        self.submit(self.student, title="未审核的稿子")

        self.login("student", self.other_student.get_id())
        response = self.client.get(reverse("material", args=["student"]))

        self.assertNotContains(response, "未审核的稿子")

    def test_other_students_get_404_on_pending_detail(self):
        self.submit(self.student)
        material = Material.objects.get()

        self.login("student", self.other_student.get_id())
        response = self.client.get(
            reverse("material_detail", args=["student", material.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_mine_filter_lists_only_own_submissions(self):
        self.submit(self.student, title="我的稿子")
        self.submit(self.other_student, title="别人的稿子")

        response = self.client.get(reverse("material", args=["student"]), {"mine": "1"})

        self.assertContains(response, "别人的稿子")
        self.assertNotContains(response, "我的稿子")

    def test_student_can_edit_own_pending_submission(self):
        self.submit(self.student)
        material = Material.objects.get()

        response = self.client.post(
            reverse("material_edit", args=["student", material.pk]),
            self.payload(title="改过的标题"),
        )
        self.assertRedirects(
            response, reverse("material_detail", args=["student", material.pk])
        )

        material.refresh_from_db()
        self.assertEqual(material.title, "改过的标题")
        self.assertEqual(material.status, Material.Status.PENDING)

    def test_student_can_delete_own_pending_submission(self):
        self.submit(self.student)
        material = Material.objects.get()

        response = self.client.post(
            reverse("material_delete", args=["student", material.pk])
        )
        self.assertRedirects(response, reverse("material", args=["student"]))
        self.assertFalse(Material.objects.filter(pk=material.pk).exists())

    def test_student_cannot_touch_another_students_submission(self):
        self.submit(self.student)
        material = Material.objects.get()

        self.login("student", self.other_student.get_id())
        self.assertEqual(
            self.client.get(
                reverse("material_edit", args=["student", material.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("material_delete", args=["student", material.pk])
            ).status_code,
            403,
        )
        self.assertTrue(Material.objects.filter(pk=material.pk).exists())


class ReviewWorkflowTests(TestCase):
    """管理员审核：通过之后才进入公共素材库。"""

    def setUp(self):
        self.student = make_student()
        self.administrator = make_administrator()
        self.category = Category.objects.create(name="测试分类甲", order=10)
        self.material = Material.objects.create(
            title="待审核的投稿",
            category=self.category,
            source="佚名",
            body="床前明月光，疑是地上霜。",
            submitted_by=self.student,
            status=Material.Status.PENDING,
        )

    def login(self, kind, uid):
        return self.client.post(
            reverse("login_detail", args=[kind]), {"uid": uid, "password": RAW_PASSWORD}
        )

    def login_student(self):
        return self.login("student", self.student.get_id())

    def login_administrator(self):
        return self.login("administrator", self.administrator.get_id())

    def review(self, action, comment=""):
        return self.client.post(
            reverse("material_review", args=["administrator", self.material.pk]),
            {"action": action, "comment": comment},
        )

    def test_student_cannot_open_the_review_page(self):
        self.login_student()
        response = self.client.get(
            reverse("material_review", args=["student", self.material.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_administrator_can_open_the_review_page(self):
        self.login_administrator()
        response = self.client.get(
            reverse("material_review", args=["administrator", self.material.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "审核素材")
        self.assertContains(response, "待审核的投稿")

    def test_approve_marks_the_material_approved(self):
        self.login_administrator()
        response = self.review("approve", "内容合适")

        self.assertRedirects(
            response,
            reverse("material_review", args=["administrator", self.material.pk]),
        )

        self.material.refresh_from_db()
        self.assertEqual(self.material.status, Material.Status.APPROVED)
        self.assertEqual(self.material.review_comment, "内容合适")
        self.assertIsNotNone(self.material.reviewed_at)

    def test_approved_material_becomes_visible_to_other_students(self):
        other = make_student(number="000009")

        self.login_administrator()
        self.review("approve")

        self.login("student", other.get_id())
        response = self.client.get(reverse("material", args=["student"]))
        self.assertContains(response, "待审核的投稿")

    def test_reject_requires_a_comment(self):
        self.login_administrator()
        response = self.review("reject", "")

        self.assertEqual(response.status_code, 200)
        self.assertIn("comment", response.context["form"].errors)

        self.material.refresh_from_db()
        self.assertEqual(self.material.status, Material.Status.PENDING)

    def test_reject_reason_is_shown_to_the_author(self):
        self.login_administrator()
        self.review("reject", "出处不明，请补充")

        self.login_student()
        response = self.client.get(
            reverse("material_detail", args=["student", self.material.pk])
        )
        self.assertContains(response, "出处不明，请补充")

    def test_editing_a_rejected_submission_sends_it_back_to_pending(self):
        self.material.status = Material.Status.REJECTED
        self.material.review_comment = "请补充出处"
        self.material.save()

        self.login_student()
        response = self.client.post(
            reverse("material_edit", args=["student", self.material.pk]),
            {
                "title": "补好出处的投稿",
                "category": self.category.pk,
                "source": "李白",
                "body": "床前明月光",
            },
        )
        self.assertRedirects(
            response, reverse("material_detail", args=["student", self.material.pk])
        )

        self.material.refresh_from_db()
        self.assertEqual(self.material.status, Material.Status.PENDING)
        self.assertEqual(self.material.review_comment, "")

    def test_approved_submission_is_locked_for_the_author(self):
        self.material.status = Material.Status.APPROVED
        self.material.save()

        self.login_student()
        self.assertEqual(
            self.client.get(
                reverse("material_edit", args=["student", self.material.pk])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("material_delete", args=["student", self.material.pk])
            ).status_code,
            403,
        )

    def test_administrator_created_material_is_approved_immediately(self):
        self.login_administrator()
        self.client.post(
            reverse("material_create", args=["administrator"]),
            {
                "title": "管理员录入",
                "category": self.category.pk,
                "source": "",
                "body": "正文",
            },
        )

        material = Material.objects.get(title="管理员录入")
        self.assertEqual(material.status, Material.Status.APPROVED)
        self.assertEqual(material.created_by, self.administrator)
        self.assertIsNone(material.submitted_by)

    def test_status_filter_narrows_the_list_for_administrators(self):
        Material.objects.create(
            title="已通过的素材", category=self.category, body="x"
        )

        self.login_administrator()
        response = self.client.get(
            reverse("material", args=["administrator"]), {"status": "pending"}
        )

        self.assertContains(response, "待审核的投稿")
        self.assertNotContains(response, "已通过的素材")

    def test_pending_count_is_shown_in_the_navigation(self):
        self.login_administrator()
        response = self.client.get(reverse("material", args=["administrator"]))

        self.assertEqual(response.context["pending_count"], 1)
        # 导航项后面跟一个数量徽章
        self.assertContains(response, '待审核<span class="nav__count">1</span>')


