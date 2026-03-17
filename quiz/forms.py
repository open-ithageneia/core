from django import forms
from import_export.forms import ImportForm

from quiz.models import ExamSession


class QuizImportForm(ImportForm):
	"""Custom import form that adds an Exam Session dropdown.

	The selected session is passed through to the Resource via
	``get_import_resource_kwargs`` so that every imported row is
	automatically linked to it.
	"""

	exam_session = forms.ModelChoiceField(
		queryset=ExamSession.objects.all(),
		required=False,
		empty_label="— none —",
		label="Exam session",
		help_text="All imported quizzes will be assigned to this exam session.",
	)

	field_order = ["resource", "exam_session", "import_file", "format"]
