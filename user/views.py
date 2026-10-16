from django.http import HttpResponse
from django.shortcuts import redirect, render

from user.cbvs import (
    CreateAdministratorView,
    CreateStudentView,
    UpdateAdministratorView,
    UpdateStudentView,
)
from user.constants import (
    GRADE_LENGTH,
    INVALID_KIND,
    KIND_ADMINISTRATOR,
    KIND_STUDENT,
    KINDS,
    UID_LENGTH,
)
from user.forms import AdmLoginForm, StuLoginForm
from user.models import Administrator, Student

LOGIN_FORMS = {
    KIND_STUDENT: StuLoginForm,
    KIND_ADMINISTRATOR: AdmLoginForm,
}

LOGIN_MODELS = {
    KIND_STUDENT: Student,
    KIND_ADMINISTRATOR: Administrator,
}

REGISTER_VIEWS = {
    KIND_STUDENT: CreateStudentView,
    KIND_ADMINISTRATOR: CreateAdministratorView,
}

UPDATE_VIEWS = {
    KIND_STUDENT: UpdateStudentView,
    KIND_ADMINISTRATOR: UpdateAdministratorView,
}


def _bad_kind():
    """kind 参数不是合法身份时统一返回 400。"""
    return HttpResponse(INVALID_KIND, status=400)


def home(request):
    """身份选择页。"""
    return render(request, "user/login_home.html")


def register_home(request):
    """注册身份选择页。"""
    return render(request, "user/register_home.html")


def login(request, kind):
    """登录：GET 渲染表单，POST 校验账号与密码。"""
    if kind not in KINDS:
        return _bad_kind()

    form_class = LOGIN_FORMS[kind]
    model = LOGIN_MODELS[kind]

    if request.method != "POST":
        context = {"kind": kind}
        initial = {}

        uid = request.GET.get("uid")
        if uid:
            context["uid"] = uid
            initial["uid"] = uid

        context["form"] = form_class(initial=initial)

        if request.GET.get("from_url"):
            context["from_url"] = request.GET.get("from_url")

        return render(request, "user/login_detail.html", context)

    form = form_class(data=request.POST)
    if form.is_valid():
        uid = form.cleaned_data["uid"]

        if len(uid) != UID_LENGTH:
            form.add_error("uid", "账号必须为 %d 位数" % UID_LENGTH)
        else:
            grade = uid[:GRADE_LENGTH]
            number = uid[GRADE_LENGTH:]
            user = model.objects.filter(grade=grade, number=number).first()

            if user is None:
                form.add_error("uid", "账号不存在")
            elif not user.check_password(form.cleaned_data["password"]):
                form.add_error("password", "密码不正确")
            else:
                request.session["kind"] = kind
                request.session["user"] = uid
                request.session["id"] = user.id
                request.session["name"] = user.name

                return redirect("material", kind=kind)

    return render(request, "user/login_detail.html", {"form": form, "kind": kind})


def logout(request):
    # flush() 会清空 session 数据并轮换 session key，避免会话固定攻击
    request.session.flush()
    return redirect("index")


def register(request, kind):
    view = REGISTER_VIEWS.get(kind)
    if view is None:
        return _bad_kind()
    return view.as_view()(request)


def update(request, kind):
    view = UPDATE_VIEWS.get(kind)
    if view is None:
        return _bad_kind()

    pk = request.session.get("id")
    if not pk:
        return redirect("login_detail", kind=kind)

    return view.as_view()(request, pk=pk)
