from django.db import models

from user.constants import KIND_ADMINISTRATOR, KIND_STUDENT
from user.models import Administrator, Student


class Category(models.Model):
    """素材分类，例如「诗词」「文言文」「写作素材」。"""

    name = models.CharField(max_length=50, unique=True, verbose_name="分类名称")
    description = models.CharField(max_length=255, blank=True, verbose_name="分类说明")
    order = models.PositiveSmallIntegerField(
        default=0, verbose_name="排序", help_text="数字越小越靠前"
    )

    class Meta:
        verbose_name = "素材分类"
        verbose_name_plural = "素材分类"
        ordering = ("order", "id")

    def __str__(self):
        return self.name


class Material(models.Model):
    """一条语文素材。

    素材有两个来源：

    * 管理员直接录入 —— 默认「已通过」，立刻对外可见；
    * 学生投稿 —— 默认「待审核」，管理员审核通过后其他人才看得到。

    一条素材只会有一个来源，所以 ``created_by`` 与 ``submitted_by`` 至多只有一个非空，
    由下面的 CheckConstraint 兜底。

    这里没有用 contenttypes 的泛型外键，是因为 ``Student`` 与 ``Administrator``
    本就是两张表，拆成两个可空外键既保留了真正的外键约束，读起来也更直白。
    """

    class Status(models.TextChoices):
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    title = models.CharField(max_length=100, verbose_name="标题")
    category = models.ForeignKey(
        Category,
        # 分类下还有素材时不允许删除，避免出现归属丢失的素材
        on_delete=models.PROTECT,
        related_name="materials",
        verbose_name="分类",
    )
    source = models.CharField(max_length=100, blank=True, verbose_name="出处/作者")
    body = models.TextField(verbose_name="正文")
    attachment = models.FileField(
        upload_to="materials/%Y/%m/",
        blank=True,
        verbose_name="附件",
        help_text="可选，支持 pdf / doc / docx / txt / md 与常见图片格式，单个不超过 10 MB",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.APPROVED,
        verbose_name="审核状态",
    )
    review_comment = models.CharField(max_length=255, blank=True, verbose_name="审核意见")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")

    created_by = models.ForeignKey(
        Administrator,
        # 录入人账号注销后素材本身应保留
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
        verbose_name="录入人（管理员）",
    )
    submitted_by = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions",
        verbose_name="投稿学生",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "素材"
        verbose_name_plural = "素材"
        ordering = ("-updated_at", "-id")
        constraints = [
            models.CheckConstraint(
                check=~models.Q(created_by__isnull=False, submitted_by__isnull=False),
                name="material_at_most_one_author",
            )
        ]

    def __str__(self):
        return self.title

    @property
    def author(self):
        """返回提交这条素材的人，可能是 Administrator 也可能是 Student。"""
        return self.submitted_by or self.created_by

    @property
    def author_kind(self):
        """返回提交者身份，取值与 URL 里的 <slug:kind> 一致。"""
        return KIND_STUDENT if self.submitted_by_id else KIND_ADMINISTRATOR

    @property
    def author_name(self):
        author = self.author
        return author.name if author else "已注销账号"

    @property
    def author_uid(self):
        author = self.author
        return author.get_id() if author else ""

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    def is_owned_by(self, person, kind):
        """这条素材是否由「当前登录的这个人」提交。

        必须同时比身份与主键：Student 与 Administrator 是两张表，主键可能撞号。
        """
        author = self.author
        return self.author_kind == kind and author is not None and author.pk == person.pk
