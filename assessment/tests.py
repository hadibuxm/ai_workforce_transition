"""Tests for the assessment app forms."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .forms import RoleAssessmentForm


class RoleAssessmentFormTests(SimpleTestCase):
    def test_requires_some_input(self):
        form = RoleAssessmentForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_rejects_both_inputs(self):
        role_file = SimpleUploadedFile("role_profile.pdf", b"fake pdf content", content_type="application/pdf")
        form = RoleAssessmentForm(
            data={"role_description": "A" * 60},
            files={"role_document": role_file},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_accepts_role_document(self):
        role_file = SimpleUploadedFile("role_profile.pdf", b"fake pdf content", content_type="application/pdf")
        form = RoleAssessmentForm(
            data={},
            files={"role_document": role_file},
        )
        self.assertTrue(form.is_valid())

    def test_accepts_role_description(self):
        form = RoleAssessmentForm(data={"role_description": "A detailed role description " * 3})
        self.assertTrue(form.is_valid())

    def test_rejects_short_role_description(self):
        form = RoleAssessmentForm(data={"role_description": "Too short"})
        self.assertFalse(form.is_valid())
        self.assertIn("role_description", form.errors)
