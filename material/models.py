from django.db import models

from user.models import Administrator


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
    """一条语文素材。管理员负责录入与维护，学生只读。"""

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
    created_by = models.ForeignKey(
        Administrator,
        # 录入人离职 / 账号注销后素材本身应保留
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
        verbose_name="录入人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "素材"
        verbose_name_plural = "素材"
        ordering = ("-updated_at", "-id")

    def __str__(self):
        return self.title
