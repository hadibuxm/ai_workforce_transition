"""Forms for capturing resume input from users."""
from django import forms
from django.core.exceptions import ValidationError


class ResumeAssessmentForm(forms.Form):
    resume_file = forms.FileField(
        label="Upload resume (PDF)",
        required=False,
        help_text="Accepted formats: PDF. File size limit 5 MB.",
    )
    job_description = forms.CharField(
        label="Paste job description",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        help_text="Provide a detailed description of the role if no resume is available.",
        max_length=4000,
    )

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    SUPPORTED_EXTENSIONS = (".pdf")

    def clean(self):
        cleaned_data = super().clean()
        file_obj = cleaned_data.get("resume_file")
        job_description = (cleaned_data.get("job_description") or "").strip()

        cleaned_data["job_description"] = job_description

        if file_obj and job_description:
            raise ValidationError("Please provide either a resume file or a job description, not both.")

        if not file_obj and not job_description:
            raise ValidationError("Upload a resume or provide a job description to continue.")

        if file_obj:
            self._validate_file(file_obj)
        else:
            self._validate_job_description(job_description)
        return cleaned_data

    def _validate_file(self, file_obj):
        if file_obj.size > self.MAX_FILE_SIZE:
            raise ValidationError("File is too large. Please upload a file under 5 MB.")

        filename = file_obj.name.lower()
        if not any(filename.endswith(ext) for ext in self.SUPPORTED_EXTENSIONS):
            raise ValidationError("Unsupported file type. Please upload a PDF or DOCX file.")

    def _validate_job_description(self, job_description: str) -> None:
        if len(job_description) < 50:
            raise ValidationError("Please provide at least 50 characters describing the role.")
