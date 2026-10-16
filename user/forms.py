from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from user.models import Administrator, Student


class LoginForm(forms.Form):
    """登录表单：10 位账号 + 密码。"""

    uid = forms.CharField(label="账号", max_length=10)
    password = forms.CharField(label="密码", max_length=128, widget=forms.PasswordInput)


class StuLoginForm(LoginForm):
    uid = forms.CharField(label="学号", max_length=10)


class AdmLoginForm(LoginForm):
    # 注意：字段名必须与 StuLoginForm 一致（都叫 uid），
    # 否则登录视图读取 cleaned_data["uid"] 时会 KeyError。
    uid = forms.CharField(label="编号", max_length=10)


class PasswordHashingMixin:
    """让 ModelForm 在保存前把 cleaned_data 里的明文密码换成哈希。

    调用方依旧按 ``form.save()`` / ``form.save(commit=False)`` 的常规方式使用表单，
    不必在视图里重复哈希逻辑。
    """

    def save(self, commit=True):
        instance = super().save(commit=False)

        raw_password = self.cleaned_data.get("password")
        if raw_password:
            instance.set_password(raw_password)

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class PersonRegisterForm(PasswordHashingMixin, forms.ModelForm):
    """注册表单的公共部分：密码 + 确认密码。

    ``clean()`` 必须定义在这里（表单类层级），写在 ``class Meta`` 里面不会被执行。
    """

    password = forms.CharField(label="密码", widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="确认密码", widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "两次输入的密码不一致")

        return cleaned_data

    def _post_clean(self):
        # 密码强度校验放在 _post_clean 而不是 clean_<field>：此时 self.instance
        # 已经由 cleaned_data 填充完毕，settings 里的
        # UserAttributeSimilarityValidator 才能拿到本次填写的邮箱参与比对。
        super()._post_clean()

        password = self.cleaned_data.get("password")
        if not password:
            return

        try:
            validate_password(password, self.instance)
        except ValidationError as error:
            self.add_error("password", error)


class StuRegisterForm(PersonRegisterForm):
    class Meta:
        model = Student
        fields = (
            "grade",
            "name",
            "password",
            "confirm_password",
            "gender",
            "birthday",
            "email",
            "info",
        )


class AdmRegisterForm(PersonRegisterForm):
    class Meta:
        model = Administrator
        fields = (
            "grade",
            "name",
            "password",
            "confirm_password",
            "gender",
            "birthday",
            "email",
            "info",
        )


class StuUpdateForm(StuRegisterForm):
    """修改学生信息：年级与学号不可改，否则账号会跟着变化。"""

    class Meta:
        model = Student
        fields = (
            "name",
            "password",
            "confirm_password",
            "gender",
            "birthday",
            "email",
            "info",
        )


class AdmUpdateForm(AdmRegisterForm):
    """修改管理员信息：年级与编号不可改，否则账号会跟着变化。"""

    class Meta:
        model = Administrator
        fields = (
            "name",
            "password",
            "confirm_password",
            "gender",
            "birthday",
            "email",
            "info",
        )
