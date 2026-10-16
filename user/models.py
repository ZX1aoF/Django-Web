from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Person(models.Model):
    """学生与管理员共用的字段与行为。

    这是一个抽象基类，不会生成数据表；具体模型见 ``Student`` 与 ``Administrator``。
    """

    GENDERS = [
        ("m", "男"),
        ("f", "女"),
    ]

    name = models.CharField(max_length=50, verbose_name="姓名")
    gender = models.CharField(max_length=10, choices=GENDERS, default="m", verbose_name="性别")
    birthday = models.DateField(verbose_name="生日")
    email = models.EmailField(verbose_name="邮箱")
    info = models.CharField(max_length=255, verbose_name="个人简介", help_text="一句话介绍自己")

    grade = models.CharField(max_length=4, verbose_name="年级")
    number = models.CharField(max_length=6, verbose_name="序号")
    # 存放的是 Django 标准密码哈希（pbkdf2_sha256，约 78 字符）而不是明文，
    # 所以长度给了 128 的余量。
    password = models.CharField(max_length=128, verbose_name="密码")

    class Meta:
        abstract = True

    def get_id(self):
        """返回登录用的 10 位账号：年级(4 位) + 序号(6 位)。"""
        return "%s%s" % (self.grade, self.number)

    def set_password(self, raw_password):
        """把明文密码哈希后写入 ``password`` 字段。"""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """校验明文密码是否与已存储的哈希匹配。"""
        return check_password(raw_password, self.password)

    def __str__(self):
        return "%s (%s)" % (self.get_id(), self.name)


class Student(Person):
    # 覆盖基类字段，仅为把 verbose_name 从「序号」改成「学号」
    number = models.CharField(max_length=6, verbose_name="学号")

    class Meta:
        verbose_name = "学生"
        verbose_name_plural = "学生"
        constraints = [
            models.UniqueConstraint(fields=["grade", "number"], name="student_id")
        ]


class Administrator(Person):
    # 覆盖基类字段，仅为把 verbose_name 从「序号」改成「编号」
    number = models.CharField(max_length=6, verbose_name="编号")

    class Meta:
        verbose_name = "管理员"
        verbose_name_plural = "管理员"
        constraints = [
            models.UniqueConstraint(fields=["grade", "number"], name="administrator_id")
        ]
