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
        job_description = form.cleaned_data.get("job_description")

        try:
            analysis: AssessmentResult = analyze_resume(
                uploaded_file=uploaded_file,
                job_description=job_description,
            )
        except UnsupportedFileType as exc:
            form.add_error("resume_file", str(exc))
            return self.form_invalid(form)
        except AnalysisError as exc:
            target_field = "job_description" if job_description and not uploaded_file else None
            if target_field:
                form.add_error(target_field, str(exc))
            else:
                form.add_error(None, str(exc))
            return self.form_invalid(form)
        except Exception:
            if job_description and not uploaded_file:
                form.add_error(
                    "job_description",
                    "We could not process this job description. Please try again with a different description.",
                )
            else:
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
