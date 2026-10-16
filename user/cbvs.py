from django.shortcuts import redirect, reverse
from django.views.generic import CreateView, UpdateView

from user.constants import KIND_ADMINISTRATOR, KIND_STUDENT, NUMBER_LENGTH
from user.forms import AdmRegisterForm, AdmUpdateForm, StuRegisterForm, StuUpdateForm
from user.models import Administrator, Student


class NextNumberMixin:
    """为新注册的用户分配该年级下的下一个序号。"""

    def get_next_number(self, grade):
        last = self.model.objects.filter(grade=grade).order_by("-number").first()
        if last is None:
            return str(1).zfill(NUMBER_LENGTH)
        return str(int(last.number) + 1).zfill(NUMBER_LENGTH)


class CreatePersonView(NextNumberMixin, CreateView):
    """注册视图的公共实现。

    ``kind`` 由子类指定，用于把注册成功后跳转的登录页与表单里的身份对应起来。
    """

    template_name = "user/register.html"
    success_url = "login_detail"
    kind = None

    def form_valid(self, form):
        # 密码已经在表单的 PasswordHashingMixin 里哈希过，这里只补上序号
        person = form.save(commit=False)
        person.number = self.get_next_number(form.cleaned_data["grade"])
        person.save()
        self.object = person

        url = "%s?uid=%s&from_url=register" % (
            reverse(self.get_success_url(), kwargs={"kind": self.kind}),
            person.get_id(),
        )
        return redirect(url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kind"] = self.kind
        return context


class CreateStudentView(CreatePersonView):
    model = Student
    form_class = StuRegisterForm
    kind = KIND_STUDENT


class CreateAdministratorView(CreatePersonView):
    # 注意：序号要基于 Administrator 表递增，用错表会跟学生的编号撞号
    model = Administrator
    form_class = AdmRegisterForm
    kind = KIND_ADMINISTRATOR


class UpdatePersonView(UpdateView):
    """修改个人信息的公共实现。"""

    template_name = "user/update.html"
    kind = None

    def get_success_url(self):
        return reverse("material", kwargs={"kind": self.kind})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kind"] = self.kind
        return context


class UpdateStudentView(UpdatePersonView):
    model = Student
    form_class = StuUpdateForm
    kind = KIND_STUDENT


class UpdateAdministratorView(UpdatePersonView):
    model = Administrator
    form_class = AdmUpdateForm
    kind = KIND_ADMINISTRATOR
