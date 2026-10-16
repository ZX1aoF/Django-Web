"""预置一批常用的语文素材分类。

这样系统刚部署起来、还没有任何素材时，新建素材的表单里就有分类可选；
管理员也可以随时在 Django Admin 里增删分类。
"""

from django.db import migrations

DEFAULT_CATEGORIES = [
    ("诗词", "古诗、词曲类素材", 10),
    ("文言文", "文言文原文、注释与译文", 20),
    ("现代文阅读", "现代文阅读段落与赏析", 30),
    ("写作素材", "作文素材、名言名句", 40),
    ("名著导读", "中外名著导读与选段", 50),
]

DEFAULT_NAMES = [name for name, _, _ in DEFAULT_CATEGORIES]


def create_default_categories(apps, schema_editor):
    Category = apps.get_model("material", "Category")
    for name, description, order in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(
            name=name,
            defaults={"description": description, "order": order},
        )


def delete_default_categories(apps, schema_editor):
    Category = apps.get_model("material", "Category")
    # 只回收还没被任何素材引用的分类，否则 Category 的 PROTECT 外键会阻止删除
    Category.objects.filter(name__in=DEFAULT_NAMES, materials__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("material", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_categories, delete_default_categories),
    ]
