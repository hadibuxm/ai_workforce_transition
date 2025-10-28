"""Tests for the assessment app forms."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .forms import ResumeAssessmentForm


class ResumeAssessmentFormTests(SimpleTestCase):
    def test_requires_some_input(self):
        form = ResumeAssessmentForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_rejects_both_inputs(self):
        resume = SimpleUploadedFile("resume.pdf", b"fake pdf content", content_type="application/pdf")
        form = ResumeAssessmentForm(
            data={"job_description": "A" * 60},
            files={"resume_file": resume},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_accepts_resume_file(self):
        resume = SimpleUploadedFile("resume.pdf", b"fake pdf content", content_type="application/pdf")
        form = ResumeAssessmentForm(
            data={},
            files={"resume_file": resume},
        )
        self.assertTrue(form.is_valid())

    def test_accepts_job_description(self):
        form = ResumeAssessmentForm(data={"job_description": "A detailed job description " * 3})
        self.assertTrue(form.is_valid())

    def test_rejects_short_job_description(self):
        form = ResumeAssessmentForm(data={"job_description": "Too short"})
        self.assertFalse(form.is_valid())
        self.assertIn("job_description", form.errors)
