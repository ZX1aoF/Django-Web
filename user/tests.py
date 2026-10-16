"""user 应用的回归测试。

这里的用例主要覆盖本次修复的缺陷，以后改动相关代码时不应该让它们变红。
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from user.forms import AdmLoginForm, AdmRegisterForm, AdmUpdateForm, StuLoginForm, StuRegisterForm, StuUpdateForm
from user.models import Administrator, Student

RAW_PASSWORD = "s3cret-pass"


def student_payload(**overrides):
    payload = {
        "grade": "2023",
        "name": "张三",
        "password": RAW_PASSWORD,
        "confirm_password": RAW_PASSWORD,
        "gender": "m",
        "birthday": "2000-01-01",
        "email": "zhangsan@example.com",
        "info": "一句话介绍自己",
    }
    payload.update(overrides)
    return payload


def administrator_payload(**overrides):
    payload = student_payload(grade="2022", name="管理员", email="admin@example.com")
    payload.update(overrides)
    return payload


def make_student(grade="2023", number="000001", name="张三"):
    student = Student(
        name=name,
        gender="m",
        birthday=date(2000, 1, 1),
        email="%s@example.com" % number,
        info="简介",
        grade=grade,
        number=number,
    )
    student.set_password(RAW_PASSWORD)
    student.save()
    return student


def make_administrator(grade="2022", number="000001", name="管理员"):
    administrator = Administrator(
        name=name,
        gender="f",
        birthday=date(1980, 5, 20),
        email="admin%s@example.com" % number,
        info="管理端账号",
        grade=grade,
        number=number,
    )
    administrator.set_password(RAW_PASSWORD)
    administrator.save()
    return administrator


class RegisterFormTests(TestCase):
    """表单层回归：``clean()`` 必须真正被执行。"""

    def test_mismatched_confirm_password_is_rejected(self):
        # 回归：clean() 曾被写在 class Meta 内部，确认密码校验从未生效
        form = StuRegisterForm(data=student_payload(confirm_password="another-pass"))
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_password", form.errors)

    def test_matching_confirm_password_passes(self):
        form = StuRegisterForm(data=student_payload())
        self.assertTrue(form.is_valid(), form.errors)

    def test_administrator_mismatch_is_rejected(self):
        # 回归：AdmRegisterForm.clean() 里曾错误引用了 StuRegisterForm
        form = AdmRegisterForm(data=administrator_payload(confirm_password="another-pass"))
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_password", form.errors)

    def test_administrator_password_field_is_a_password_input(self):
        # 回归：AdmRegisterForm 没声明 password，ModelForm 会渲染成明文输入框
        widget = AdmRegisterForm().fields["password"].widget
        self.assertEqual(widget.input_type, "password")

    def test_update_forms_do_not_expose_grade(self):
        # 年级/序号不可改，否则账号会变化、登录状态失效
        self.assertNotIn("grade", StuUpdateForm().fields)
        self.assertNotIn("number", StuUpdateForm().fields)
        self.assertNotIn("grade", AdmUpdateForm().fields)
        self.assertNotIn("number", AdmUpdateForm().fields)


class LoginFormTests(TestCase):
    def test_login_forms_share_the_uid_field_name(self):
        # 回归：管理员登录表单字段曾叫 aid，而视图统一读 cleaned_data["uid"]，会 KeyError
        self.assertIn("uid", StuLoginForm().fields)
        self.assertIn("uid", AdmLoginForm().fields)
        self.assertNotIn("aid", AdmLoginForm().fields)


class RegisterViewTests(TestCase):
    def test_first_number_is_000001(self):
        self.client.post(reverse("register_detail", args=["student"]), student_payload())
        student = Student.objects.get()
        self.assertEqual(student.number, "000001")
        self.assertEqual(student.get_id(), "2023000001")

    def test_number_increments_within_one_grade(self):
        for name in ("张三", "李四", "王五"):
            self.client.post(reverse("register_detail", args=["student"]), student_payload(name=name))
        numbers = list(Student.objects.order_by("number").values_list("number", flat=True))
        self.assertEqual(numbers, ["000001", "000002", "000003"])

    def test_administrator_number_does_not_follow_students(self):
        # 回归：CreateAdministratorView 曾用 Student 表计算下一个编号，会与学生撞号
        self.client.post(reverse("register_detail", args=["student"]), student_payload())
        self.client.post(
            reverse("register_detail", args=["administrator"]),
            administrator_payload(grade="2023"),
        )
        self.assertEqual(Student.objects.get().number, "000001")
        self.assertEqual(Administrator.objects.get().number, "000001")

    def test_password_is_stored_as_hash(self):
        # 回归：密码曾经是明文存储
        self.client.post(reverse("register_detail", args=["student"]), student_payload())
        student = Student.objects.get()
        self.assertNotEqual(student.password, RAW_PASSWORD)
        self.assertTrue(student.check_password(RAW_PASSWORD))
        self.assertFalse(student.check_password("wrong-pass"))

    def test_register_redirect_reports_the_new_number(self):
        # 回归：login_detail.html 的块名曾写成 welcome-message，与父模板的
        # welcome_message 不匹配，注册成功的提示从来没有渲染出来过
        response = self.client.post(
            reverse("register_detail", args=["student"]), student_payload(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "注册成功")
        self.assertContains(response, "2023000001")

    def test_invalid_kind_returns_400(self):
        response = self.client.get(reverse("register_detail", args=["teacher"]))
        self.assertEqual(response.status_code, 400)


class LoginViewTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.administrator = make_administrator()

    def test_student_can_log_in(self):
        response = self.client.post(
            reverse("login_detail", args=["student"]),
            {"uid": self.student.get_id(), "password": RAW_PASSWORD},
        )
        self.assertRedirects(response, reverse("material", args=["student"]))

    def test_administrator_can_log_in(self):
        # 回归：管理员登录曾经完全不可用（字段名不一致 + 身份白名单写错）
        response = self.client.post(
            reverse("login_detail", args=["administrator"]),
            {"uid": self.administrator.get_id(), "password": RAW_PASSWORD},
        )
        self.assertRedirects(response, reverse("material", args=["administrator"]))

    def test_wrong_password_shows_error(self):
        response = self.client.post(
            reverse("login_detail", args=["student"]),
            {"uid": self.student.get_id(), "password": "wrong-pass"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "密码不正确")

    def test_unknown_account_shows_error(self):
        response = self.client.post(
            reverse("login_detail", args=["student"]),
            {"uid": "2023999999", "password": RAW_PASSWORD},
        )
        self.assertContains(response, "账号不存在")

    def test_uid_must_be_ten_digits(self):
        response = self.client.post(
            reverse("login_detail", args=["student"]),
            {"uid": "2023", "password": RAW_PASSWORD},
        )
        self.assertContains(response, "账号必须为 10 位数")

    def test_account_is_only_valid_for_its_own_kind(self):
        # 学生的账号在管理员入口应该查不到，两个表是独立的
        response = self.client.post(
            reverse("login_detail", args=["administrator"]),
            {"uid": self.student.get_id(), "password": RAW_PASSWORD},
        )
        self.assertContains(response, "账号不存在")

    def test_get_prefills_uid_after_register(self):
        response = self.client.get(
            reverse("login_detail", args=["student"]),
            {"uid": "2023000001", "from_url": "register"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2023000001")

    def test_invalid_kind_returns_400(self):
        response = self.client.get(reverse("login_detail", args=["teacher"]))
        self.assertEqual(response.status_code, 400)


class LogoutViewTests(TestCase):
    def test_logout_clears_session(self):
        student = make_student()
        self.client.post(
            reverse("login_detail", args=["student"]),
            {"uid": student.get_id(), "password": RAW_PASSWORD},
        )
        self.assertRedirects(self.client.get(reverse("logout")), reverse("index"))
        self.assertRedirects(
            self.client.get(reverse("material", args=["student"])),
            reverse("login_detail", args=["student"]),
        )


class UpdateViewTests(TestCase):
    def setUp(self):
        self.student = make_student()
        self.client.post(
            reverse("login_detail", args=["student"]),
            {"uid": self.student.get_id(), "password": RAW_PASSWORD},
        )

    def update_payload(self, **overrides):
        payload = {
            "name": "张三改",
            "password": "new-pass-123",
            "confirm_password": "new-pass-123",
            "gender": "f",
            "birthday": "2001-02-03",
            "email": "new@example.com",
            "info": "改过了",
        }
        payload.update(overrides)
        return payload

    def test_update_page_renders(self):
        response = self.client.get(reverse("update", args=["student"]))
        self.assertEqual(response.status_code, 200)

    def test_update_rehashes_the_new_password(self):
        response = self.client.post(reverse("update", args=["student"]), self.update_payload())
        self.assertRedirects(response, reverse("material", args=["student"]))

        self.student.refresh_from_db()
        self.assertEqual(self.student.name, "张三改")
        self.assertEqual(self.student.gender, "f")
        self.assertTrue(self.student.check_password("new-pass-123"))
        self.assertFalse(self.student.check_password(RAW_PASSWORD))

    def test_update_rejects_mismatched_confirm_password(self):
        response = self.client.post(
            reverse("update", args=["student"]),
            self.update_payload(confirm_password="another-pass"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "两次输入的密码不一致")
        self.student.refresh_from_db()
        self.assertEqual(self.student.name, "张三")

    def test_update_requires_login(self):
        self.client.get(reverse("logout"))
        self.assertRedirects(
            self.client.get(reverse("update", args=["student"])),
            reverse("login_detail", args=["student"]),
        )


class AdministratorUpdateViewTests(TestCase):
    def test_administrator_can_update_profile(self):
        administrator = make_administrator()
        self.client.post(
            reverse("login_detail", args=["administrator"]),
            {"uid": administrator.get_id(), "password": RAW_PASSWORD},
        )

        payload = {
            "name": "管理员改",
            "password": "admin-pass-456",
            "confirm_password": "admin-pass-456",
            "gender": "m",
            "birthday": "1981-06-21",
            "email": "admin-new@example.com",
            "info": "改过了",
        }
        response = self.client.post(reverse("update", args=["administrator"]), payload)
        self.assertRedirects(response, reverse("material", args=["administrator"]))

        administrator.refresh_from_db()
        self.assertEqual(administrator.name, "管理员改")
        self.assertTrue(administrator.check_password("admin-pass-456"))


class StaticPageTests(TestCase):
    def test_index_page_renders(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "学生登录")

    def test_login_chooser_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "管理员登录")

    def test_register_chooser_page_renders(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "注册学生")

    def test_admin_site_is_routed(self):
        # 回归：urls.py 里 import 了 admin 却没挂路由，/admin/ 一直是 404
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/admin/login/"))
