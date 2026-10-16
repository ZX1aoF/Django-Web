"""把历史上以明文保存的密码批量转换成 Django 密码哈希。

识别方式：能被 ``identify_hasher`` 解析出已知算法名的视为「已经是哈希」，
其余一律当作明文重新哈希。哈希不可逆，所以没有反向操作。
"""

from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def is_hashed(value):
    """判断字符串是否已经是 Django 能识别的密码哈希。"""
    try:
        identify_hasher(value)
    except ValueError:
        return False
    return True


def hash_plaintext_passwords(apps, schema_editor):
    for model_name in ("Student", "Administrator"):
        model = apps.get_model("user", model_name)
        for person in model.objects.all():
            if not person.password or is_hashed(person.password):
                continue
            person.password = make_password(person.password)
            person.save(update_fields=["password"])


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0002_widen_password_field"),
    ]

    operations = [
        migrations.RunPython(hash_plaintext_passwords, migrations.RunPython.noop),
    ]
