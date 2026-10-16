from django.http import HttpResponse
from django.shortcuts import redirect, render

from user.constants import (
    GRADE_LENGTH,
    INVALID_KIND,
    KIND_ADMINISTRATOR,
    KIND_STUDENT,
    KINDS,
    UID_LENGTH,
)
from user.models import Administrator, Student

MODELS = {
    KIND_STUDENT: Student,
    KIND_ADMINISTRATOR: Administrator,
}


def get_user(request, kind):
    """按 session 取出当前登录的用户。

    :param kind: ``student`` 或 ``administrator``
    :return: 对应的 Student / Administrator 实例；未登录或身份不符时返回 None
    """
    if kind not in KINDS or request.session.get("kind") != kind:
        return None

    uid = request.session.get("user", "")
    if len(uid) != UID_LENGTH:
        return None

    grade = uid[:GRADE_LENGTH]
    number = uid[GRADE_LENGTH:]
    return MODELS[kind].objects.filter(grade=grade, number=number).first()


def home(request, kind):
    """登录后的资料页，未登录则跳回对应身份的登录页。"""
    if kind not in KINDS:
        return HttpResponse(INVALID_KIND, status=400)

    user = get_user(request, kind)
    if user is None:
        return redirect("login_detail", kind=kind)

    info = {
        "name": user.name,
        "kind": kind,
    }

    return render(request, "material/nav.html", {"info": info})
