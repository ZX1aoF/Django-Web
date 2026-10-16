from django.contrib import admin

from user.models import Administrator, Student


class PersonAdmin(admin.ModelAdmin):
    list_display = ("account", "name", "gender", "grade", "number", "birthday", "email")
    list_filter = ("gender", "grade")
    search_fields = ("name", "email", "grade", "number")
    # 密码存的是哈希，展示出来没有意义，也不允许在后台手改
    exclude = ("password",)

    @admin.display(description="账号", ordering=("grade", "number"))
    def account(self, obj):
        return obj.get_id()


@admin.register(Student)
class StudentAdmin(PersonAdmin):
    pass


@admin.register(Administrator)
class AdministratorAdmin(PersonAdmin):
    pass
