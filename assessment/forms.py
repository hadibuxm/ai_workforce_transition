"""Forms for capturing role assessment input and controlling access."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import AccessCode


class RoleAssessmentForm(forms.Form):
    role_document = forms.FileField(
        label="Upload role profile (PDF)",
        required=False,
        help_text="Accepted formats: PDF. File size limit 5 MB.",
    )
    role_description = forms.CharField(
        label="Paste role description",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        help_text="Provide a detailed description of the role if no document is available.",
        max_length=4000,
    )

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    SUPPORTED_EXTENSIONS = (".pdf")

    def clean(self):
        cleaned_data = super().clean()
        file_obj = cleaned_data.get("role_document")
        role_description = (cleaned_data.get("role_description") or "").strip()

        cleaned_data["role_description"] = role_description

        if file_obj and role_description:
            raise ValidationError("Please provide either a role document or a role description, not both.")

        if not file_obj and not role_description:
            raise ValidationError("Upload a role document or provide a role description to continue.")

        if file_obj:
            self._validate_file(file_obj)
        else:
            self._validate_role_description(role_description)
        return cleaned_data

    def _validate_file(self, file_obj):
        if file_obj.size > self.MAX_FILE_SIZE:
            raise ValidationError({"role_document": "File is too large. Please upload a file under 5 MB."})

        filename = file_obj.name.lower()
        if not any(filename.endswith(ext) for ext in self.SUPPORTED_EXTENSIONS):
            raise ValidationError({"role_document": "Unsupported file type. Please upload a PDF or DOCX file."})

    def _validate_role_description(self, role_description: str) -> None:
        if len(role_description) < 50:
            raise ValidationError({"role_description": "Please provide at least 50 characters describing the role."})


class SignupForm(UserCreationForm):
    access_code = forms.CharField(
        label="Single-use access code",
        max_length=64,
        help_text="Enter the access code that was shared with you.",
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self._access_code_instance = None

    def clean_access_code(self):
        raw_code = (self.cleaned_data.get("access_code") or "").strip()
        if not raw_code:
            raise ValidationError("Access code is required.")

        try:
            access_code = AccessCode.objects.get(code__iexact=raw_code, used_by__isnull=True)
        except AccessCode.DoesNotExist as exc:
            raise ValidationError("That access code is invalid or has already been used.") from exc

        self._access_code_instance = access_code
        return access_code.code

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            self._mark_code_used(user)
        else:
            self._pending_user = user
        return user

    def save_m2m(self):
        super().save_m2m()
        pending_user = getattr(self, "_pending_user", None)
        if pending_user is not None:
            self._mark_code_used(pending_user)
            delattr(self, "_pending_user")

    def _mark_code_used(self, user):
        code = getattr(self, "_access_code_instance", None)
        if code and not code.is_used:
            code.mark_used(user)
