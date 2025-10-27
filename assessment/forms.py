"""Forms for capturing resume input from users."""
from django import forms
from django.core.exceptions import ValidationError


class ResumeAssessmentForm(forms.Form):
    resume_file = forms.FileField(
        label="Upload resume (PDF or Word)",
        required=True,
        help_text="Accepted formats: PDF, DOCX. File size limit 5 MB.",
    )

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    SUPPORTED_EXTENSIONS = (".pdf", ".docx")

    def clean(self):
        cleaned_data = super().clean()
        file_obj = cleaned_data.get("resume_file")

        if not file_obj:
            raise ValidationError("Upload a resume file to continue.")

        self._validate_file(file_obj)
        return cleaned_data

    def _validate_file(self, file_obj):
        if file_obj.size > self.MAX_FILE_SIZE:
            raise ValidationError("File is too large. Please upload a file under 5 MB.")

        filename = file_obj.name.lower()
        if not any(filename.endswith(ext) for ext in self.SUPPORTED_EXTENSIONS):
            raise ValidationError("Unsupported file type. Please upload a PDF or DOCX file.")
