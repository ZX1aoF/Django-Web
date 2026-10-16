"""material 应用的回归测试。"""

import shutil
import tempfile
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import ProtectedError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from material.models import Category, Material
from material.views import get_user
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
    """学生只能看，不能改。"""

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

    def test_student_cannot_open_create_page(self):
        response = self.client.get(reverse("material_create", args=["student"]))
        self.assertEqual(response.status_code, 403)

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

