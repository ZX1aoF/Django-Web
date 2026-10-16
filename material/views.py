from functools import wraps

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from material.forms import MaterialForm
from material.models import Category, Material
from user.constants import (
    GRADE_LENGTH,
    INVALID_KIND,
    KIND_ADMINISTRATOR,
    KIND_STUDENT,
    KINDS,
    PERMISSION_DENIED,
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


def require_person(administrator_only=False):
    """视图装饰器：要求已登录（可选再要求管理员身份）。

    校验通过后把当前用户挂到 ``request.person``、身份挂到 ``request.kind``，
    视图里就不必再自己查一遍 session。
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, kind, *args, **kwargs):
            if kind not in KINDS:
                return HttpResponse(INVALID_KIND, status=400)

            person = get_user(request, kind)
            if person is None:
                return redirect("login_detail", kind=kind)

            if administrator_only and kind != KIND_ADMINISTRATOR:
                return HttpResponse(PERMISSION_DENIED, status=403)

            request.person = person
            request.kind = kind
            return view(request, kind, *args, **kwargs)

        return wrapper

    return decorator


def base_context(request, **extra):
    """素材库各页面共用的上下文：nav.html 需要 info 与 is_administrator。"""
    context = {
        "info": {"name": request.person.name, "kind": request.kind},
        "is_administrator": request.kind == KIND_ADMINISTRATOR,
    }
    context.update(extra)
    return context


@require_person()
def home(request, kind):
    """素材库首页：支持按分类筛选与关键词搜索。"""
    category_id = request.GET.get("category", "")
    keyword = request.GET.get("q", "").strip()

    materials = Material.objects.select_related("category", "created_by")

    if category_id.isdigit():
        materials = materials.filter(category_id=int(category_id))

    if keyword:
        materials = materials.filter(
            Q(title__icontains=keyword)
            | Q(source__icontains=keyword)
            | Q(body__icontains=keyword)
        )

    context = base_context(
        request,
        materials=materials,
        categories=Category.objects.all(),
        current_category=category_id,
        keyword=keyword,
    )
    return render(request, "material/list.html", context)


@require_person()
def detail(request, kind, pk):
    """素材详情，学生与管理员都能看。"""
    material = get_object_or_404(
        Material.objects.select_related("category", "created_by"), pk=pk
    )
    return render(request, "material/detail.html", base_context(request, material=material))


@require_person(administrator_only=True)
def create(request, kind):
    """新建素材，仅管理员。"""
    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.created_by = request.person
            material.save()
            messages.success(request, "素材《%s》已创建。" % material.title)
            return redirect("material_detail", kind=kind, pk=material.pk)
    else:
        form = MaterialForm()

    return render(
        request, "material/form.html", base_context(request, form=form, material=None)
    )


@require_person(administrator_only=True)
def edit(request, kind, pk):
    """编辑素材，仅管理员。"""
    material = get_object_or_404(Material, pk=pk)

    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, "素材《%s》已更新。" % material.title)
            return redirect("material_detail", kind=kind, pk=material.pk)
    else:
        form = MaterialForm(instance=material)

    return render(
        request,
        "material/form.html",
        base_context(request, form=form, material=material),
    )


@require_person(administrator_only=True)
def delete(request, kind, pk):
    """删除素材，仅管理员。GET 先确认，POST 才真正删除。"""
    material = get_object_or_404(Material, pk=pk)

    if request.method == "POST":
        title = material.title
        material.delete()
        messages.success(request, "素材《%s》已删除。" % title)
        return redirect("material", kind=kind)

    return render(
        request,
        "material/confirm_delete.html",
        base_context(request, material=material),
    )
