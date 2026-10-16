from functools import wraps

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from material.forms import MaterialForm, ReviewForm
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

# 学生处于这两种状态时还能自己改稿 / 重投；一旦通过就锁住，不能再改已发布的内容
STUDENT_EDITABLE_STATUSES = (Material.Status.PENDING, Material.Status.REJECTED)


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


def base_context(request, nav=None, **extra):
    """素材库各页面共用的上下文。

    ``nav`` 用来标记侧边导航当前高亮哪一项（library / create / mine / pending）。
    """
    context = {
        "info": {"name": request.person.name, "kind": request.kind},
        "is_administrator": request.kind == KIND_ADMINISTRATOR,
        "nav": nav,
    }

    if request.kind == KIND_ADMINISTRATOR:
        # 让导航栏上的「待审核」带上数量，管理员一眼能看到有没有活儿
        context["pending_count"] = Material.objects.filter(
            status=Material.Status.PENDING
        ).count()

    context.update(extra)
    return context


def visible_materials(kind, person):
    """当前身份能看到的素材集合。

    * 管理员：全部；
    * 学生：已通过的公共素材，外加自己投的全部稿件（含待审核 / 已驳回）。
    """
    queryset = Material.objects.select_related("category", "created_by", "submitted_by")

    if kind == KIND_ADMINISTRATOR:
        return queryset

    return queryset.filter(Q(status=Material.Status.APPROVED) | Q(submitted_by=person))


def can_manage(material, kind, person):
    """能否编辑 / 删除这条素材。

    管理员不受限制；学生只能管自己还没通过审核的投稿。
    """
    if kind == KIND_ADMINISTRATOR:
        return True
    return material.is_owned_by(person, kind) and material.status in STUDENT_EDITABLE_STATUSES


def build_stats(kind, person):
    """列表页顶部的统计卡。

    管理员看全局，学生看「素材库 + 自己的投稿」。
    两边都只用一次聚合查询算出全部计数。
    """
    if kind == KIND_ADMINISTRATOR:
        counts = Material.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=Material.Status.PENDING)),
            approved=Count("id", filter=Q(status=Material.Status.APPROVED)),
            rejected=Count("id", filter=Q(status=Material.Status.REJECTED)),
        )
        return [
            {"label": "素材总数", "value": counts["total"], "primary": True},
            {"label": "待审核", "value": counts["pending"]},
            {"label": "已通过", "value": counts["approved"]},
            {"label": "已驳回", "value": counts["rejected"]},
        ]

    counts = Material.objects.filter(submitted_by=person).aggregate(
        total=Count("id"),
        pending=Count("id", filter=Q(status=Material.Status.PENDING)),
        approved=Count("id", filter=Q(status=Material.Status.APPROVED)),
    )
    return [
        {
            "label": "素材库",
            "value": Material.objects.filter(status=Material.Status.APPROVED).count(),
            "primary": True,
        },
        {"label": "我的投稿", "value": counts["total"]},
        {"label": "待审核", "value": counts["pending"]},
        {"label": "已通过", "value": counts["approved"]},
    ]


@require_person()
def home(request, kind):
    """素材库：按分类 / 关键词 / 状态筛选，学生可以只看自己的投稿。"""
    category_id = request.GET.get("category", "")
    keyword = request.GET.get("q", "").strip()
    current_status = request.GET.get("status", "")
    mine = request.GET.get("mine") == "1"

    materials = visible_materials(kind, request.person)

    if category_id.isdigit():
        materials = materials.filter(category_id=int(category_id))

    if keyword:
        materials = materials.filter(
            Q(title__icontains=keyword)
            | Q(source__icontains=keyword)
            | Q(body__icontains=keyword)
        )

    # 状态筛选只对管理员开放：学生本来就看不到别人的待审核稿件
    if kind == KIND_ADMINISTRATOR and current_status in Material.Status.values:
        materials = materials.filter(status=current_status)

    if mine:
        if kind == KIND_ADMINISTRATOR:
            materials = materials.filter(created_by=request.person)
        else:
            materials = materials.filter(submitted_by=request.person)

    materials = list(materials)
    for material in materials:
        material.can_manage = can_manage(material, kind, request.person)

    # 侧边导航高亮：只看自己的投稿 / 管理员的待审核队列 / 其余都算素材库
    if mine:
        nav = "mine"
    elif kind == KIND_ADMINISTRATOR and current_status == Material.Status.PENDING:
        nav = "pending"
    else:
        nav = "library"

    context = base_context(
        request,
        nav=nav,
        materials=materials,
        stats=build_stats(kind, request.person),
        categories=Category.objects.all(),
        status_choices=Material.Status.choices,
        current_category=category_id,
        current_status=current_status,
        keyword=keyword,
        mine=mine,
    )
    return render(request, "material/list.html", context)


@require_person()
def detail(request, kind, pk):
    """素材详情。

    直接拿可见集合去查，所以学生访问别人的待审核稿件会得到 404，
    既看不到内容，也探测不出这条记录存不存在。
    """
    material = get_object_or_404(visible_materials(kind, request.person), pk=pk)

    context = base_context(
        request,
        material=material,
        can_manage=can_manage(material, kind, request.person),
    )
    return render(request, "material/detail.html", context)


@require_person()
def create(request, kind):
    """新建素材。管理员录入即发布，学生投稿进入待审核。"""
    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)

            if kind == KIND_ADMINISTRATOR:
                material.created_by = request.person
                material.status = Material.Status.APPROVED
            else:
                material.submitted_by = request.person
                material.status = Material.Status.PENDING

            material.save()

            if kind == KIND_ADMINISTRATOR:
                messages.success(request, "素材《%s》已创建。" % material.title)
            else:
                messages.success(request, "投稿《%s》已提交，等待管理员审核。" % material.title)

            return redirect("material_detail", kind=kind, pk=material.pk)
    else:
        form = MaterialForm()

    return render(
        request,
        "material/form.html",
        base_context(request, nav="create", form=form, material=None),
    )


@require_person()
def edit(request, kind, pk):
    """编辑素材：管理员可改全部，学生只能改自己待审核 / 已驳回的稿。"""
    material = get_object_or_404(Material, pk=pk)

    if not can_manage(material, kind, request.person):
        return HttpResponse(PERMISSION_DENIED, status=403)

    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            material = form.save(commit=False)

            if kind == KIND_STUDENT:
                # 学生改完自己的稿子要重新走一遍审核，并清掉上一次的审核结论
                material.status = Material.Status.PENDING
                material.review_comment = ""
                material.reviewed_at = None

            material.save()
            messages.success(request, "素材《%s》已更新。" % material.title)
            return redirect("material_detail", kind=kind, pk=material.pk)
    else:
        form = MaterialForm(instance=material)

    return render(
        request,
        "material/form.html",
        base_context(request, form=form, material=material),
    )


@require_person()
def delete(request, kind, pk):
    """删除素材：权限同编辑。GET 先确认，POST 才真正删除。"""
    material = get_object_or_404(Material, pk=pk)

    if not can_manage(material, kind, request.person):
        return HttpResponse(PERMISSION_DENIED, status=403)

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


@require_person(administrator_only=True)
def review(request, kind, pk):
    """审核素材，仅管理员。"""
    material = get_object_or_404(Material, pk=pk)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            approved = form.cleaned_data["action"] == ReviewForm.ACTION_APPROVE

            material.status = (
                Material.Status.APPROVED if approved else Material.Status.REJECTED
            )
            material.review_comment = form.cleaned_data["comment"]
            material.reviewed_at = timezone.now()
            material.save(update_fields=["status", "review_comment", "reviewed_at"])

            messages.success(
                request,
                "素材《%s》已%s。" % (material.title, "通过" if approved else "驳回"),
            )
            return redirect("material_review", kind=kind, pk=material.pk)
    else:
        form = ReviewForm()

    return render(
        request,
        "material/review.html",
        base_context(request, material=material, form=form),
    )
