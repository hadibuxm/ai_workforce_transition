"""Views for the Transition Assessment Tool."""
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import RoleAssessmentForm, SignupForm
from .models import UserProfile
from .services import AnalysisError, AssessmentResult, UnsupportedFileType, analyze_role


class AssessmentView(LoginRequiredMixin, FormView):
    template_name = "assessment/home.html"
    form_class = RoleAssessmentForm
    success_url = "/"
    login_url = reverse_lazy("login")

    def form_valid(self, form):
        profile = self._get_user_profile()
        if profile.runs_remaining <= 0:
            form.add_error(None, "You have used all five assessments available on your account.")
            return self.form_invalid(form)

        uploaded_file = form.cleaned_data.get("role_document")
        role_description = form.cleaned_data.get("role_description")

        try:
            analysis: AssessmentResult = analyze_role(
                uploaded_file=uploaded_file,
                role_description=role_description,
            )
        except UnsupportedFileType as exc:
            form.add_error("role_document", str(exc))
            return self.form_invalid(form)
        except AnalysisError as exc:
            target_field = "role_description" if role_description and not uploaded_file else None
            if target_field:
                form.add_error(target_field, str(exc))
            else:
                form.add_error(None, str(exc))
            return self.form_invalid(form)
        except Exception:
            if role_description and not uploaded_file:
                form.add_error(
                    "role_description",
                    "We could not process this role description. Please try again with a different description.",
                )
            else:
                form.add_error(
                    "role_document",
                    "We could not process this file. Please upload a different PDF or DOCX.",
                )
            return self.form_invalid(form)
        else:
            profile.decrement_run()

        context = self.get_context_data(
            form=self.form_class(),
            result=analysis,
        )
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            profile = self._get_user_profile()
            context["remaining_runs"] = profile.runs_remaining
            context["total_runs_allowed"] = UserProfile.DEFAULT_RUN_ALLOWANCE
        return context

    def _get_user_profile(self) -> UserProfile:
        profile = getattr(self.request.user, "assessment_profile", None)
        if profile is None:
            profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class SignupView(FormView):
    template_name = "registration/signup.html"
    form_class = SignupForm
    success_url = reverse_lazy("assessment:home")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


def logout_view(request):
    """Log the user out and return them to the login screen."""
    logout(request)
    return redirect("login")
