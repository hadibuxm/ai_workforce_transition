"""Forms for capturing role assessment input from users."""
from django import forms
from django.core.exceptions import ValidationError


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
            raise ValidationError("File is too large. Please upload a file under 5 MB.")

        filename = file_obj.name.lower()
        if not any(filename.endswith(ext) for ext in self.SUPPORTED_EXTENSIONS):
            raise ValidationError("Unsupported file type. Please upload a PDF or DOCX file.")

    def _validate_role_description(self, role_description: str) -> None:
        if len(role_description) < 50:
            raise ValidationError("Please provide at least 50 characters describing the role.")
