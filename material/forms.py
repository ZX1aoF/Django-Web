from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from material.models import Material

ALLOWED_ATTACHMENT_EXTENSIONS = (
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".md",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
)

MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_attachment(file):
    """限制附件扩展名与体积，避免上传可执行文件或超大文件。"""
    extension = Path(file.name).suffix.lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise ValidationError(
            "不支持的附件格式「%s」，仅允许：%s"
            % (extension or "无扩展名", "、".join(ALLOWED_ATTACHMENT_EXTENSIONS))
        )

    size = getattr(file, "size", None)
    if size and size > MAX_ATTACHMENT_SIZE:
        raise ValidationError(
            "附件不能超过 10 MB，当前为 %.1f MB" % (size / 1024 / 1024)
        )


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ("title", "category", "source", "body", "attachment")
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "例如：静夜思"}),
            "source": forms.TextInput(attrs={"placeholder": "例如：李白《静夜思》"}),
            "body": forms.Textarea(attrs={"rows": 14}),
        }

    def clean_attachment(self):
        attachment = self.cleaned_data.get("attachment")
        if attachment:
            validate_attachment(attachment)
        return attachment


class ReviewForm(forms.Form):
    """管理员审核素材时填写的表单。"""

    ACTION_APPROVE = "approve"
    ACTION_REJECT = "reject"

    action = forms.ChoiceField(
        label="审核结果",
        choices=[
            (ACTION_APPROVE, "通过"),
            (ACTION_REJECT, "驳回"),
        ],
        widget=forms.RadioSelect,
        initial=ACTION_APPROVE,
    )
    comment = forms.CharField(
        label="审核意见",
        required=False,
        max_length=255,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "驳回时请写明原因，投稿的学生可以看到"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        # 驳回必须说明原因，否则学生不知道要改什么
        if cleaned_data.get("action") == self.ACTION_REJECT and not cleaned_data.get("comment"):
            self.add_error("comment", "驳回时必须填写原因")

        return cleaned_data
