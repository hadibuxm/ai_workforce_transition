"""Views for the Transition Assessment Tool."""
from django.views.generic import FormView

from .forms import ResumeAssessmentForm
from .services import AnalysisError, AssessmentResult, UnsupportedFileType, analyze_resume


class AssessmentView(FormView):
    template_name = "assessment/home.html"
    form_class = ResumeAssessmentForm
    success_url = "/"

    def form_valid(self, form):
        uploaded_file = form.cleaned_data.get("resume_file")

        try:
            analysis: AssessmentResult = analyze_resume(uploaded_file)
        except UnsupportedFileType as exc:
            form.add_error("resume_file", str(exc))
            return self.form_invalid(form)
        except AnalysisError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        except Exception:
            form.add_error(
                "resume_file",
                "We could not process this file. Please upload a different PDF or DOCX.",
            )
            return self.form_invalid(form)

        context = self.get_context_data(
            form=self.form_class(),
            result=analysis,
        )
        return self.render_to_response(context)
