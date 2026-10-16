"""material 应用的回归测试。"""

from datetime import date

from django.test import RequestFactory, TestCase
from django.urls import reverse

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
