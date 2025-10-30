"""Views for the Transition Assessment Tool."""
from django.views.generic import FormView

from .forms import RoleAssessmentForm
from .services import AnalysisError, AssessmentResult, UnsupportedFileType, analyze_role


class AssessmentView(FormView):
    template_name = "assessment/home.html"
    form_class = RoleAssessmentForm
    success_url = "/"

    def form_valid(self, form):
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

        context = self.get_context_data(
            form=self.form_class(),
            result=analysis,
        )
        return self.render_to_response(context)
