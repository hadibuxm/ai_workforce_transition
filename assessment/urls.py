"""URL patterns for the assessment app."""
from django.urls import path

from . import views

app_name = "assessment"

urlpatterns = [
    path("", views.AssessmentView.as_view(), name="home"),
]

