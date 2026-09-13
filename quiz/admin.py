import copy
import logging
import zipfile

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin

from open_ithageneia.utils import get_admin_image_thumb_preview

from .models import (
	fold_for_search,
	DragAndDrop,
	DragAndDropValue,
	FillInTheBlank,
	FillInTheBlankExtraChoice,
	FillInTheBlankText,
	Listening,
	ListeningPart,
	MapArea,
	MapPointer,
	MapPointerAnswer,
	MapPointerAnswerArea,
	MatchPair,
	Matching,
	OpenEnded,
	OpenEndedAnswer,
	QuizAsset,
	QuizCategory,
	Statement,
	StatementChoice,
	validate_listening_question_types,
)
from .resources import (
	FillInTheBlankResource,
	StatementResource,
	DragAndDropResource,
	MatchingResource,
	clear_image_store,
	load_images_from_zip,
	OpenEndedResource,
)

logger = logging.getLogger(__name__)


def without_category(fields):
	"""``fields`` minus ``category``.

	Some quiz types only ever belong to one category, so on their pages the
	picker, the column and the filter are all noise. See
	``FixedCategoryFormMixin`` for how the value gets set once the field is gone.
	"""
	return [field for field in fields if field != "category"]


class FixedCategoryFormMixin:
	"""Stamps ``fixed_category`` on the instance being saved, for the admin pages
	that leave ``category`` out of their fields.

	The stamp has to happen here rather than through a model default: a field the
	admin does not render is one nothing fills in, and the value is a property of
	the page (a listening question is a listening question) rather than of the
	table. Setting it on ``self.instance`` — not as form ``initial``, which only
	feeds rendered fields — puts it in place before validation, and Django's
	``_post_clean`` leaves fields the form does not carry alone, so it survives to
	the save.
	"""

	fixed_category = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.instance.category_id = self.fixed_category


# ---------------------------------------------------------------------------
# Editing a list of plain strings as one textarea.
#
# Alternatives are child rows two levels below the question, and Django has no
# nested inlines. Rather than send authors to a separate page per answer, the
# answer's alternatives are edited as one line-per-alternative textarea and
# written back as rows on save.
# ---------------------------------------------------------------------------


class LineListField(forms.CharField):
	"""A textarea whose value is a list of non-empty, stripped lines."""

	widget = forms.Textarea(attrs={"rows": 3, "cols": 40})

	def prepare_value(self, value):
		if isinstance(value, (list, tuple)):
			return "\n".join(value)
		return value

	def clean(self, value):
		value = super().clean(value)
		return [line.strip() for line in (value or "").splitlines() if line.strip()]


def sync_line_rows(related_manager, texts, text_field="text"):
	"""Make *related_manager*'s rows match *texts*, in order.

	Delete-then-recreate rather than diffing: these rows carry nothing but their
	text and position, so there is no identity worth preserving, and a rewrite is
	what the importer has always done too.
	"""
	related_manager.all().delete()
	model = related_manager.model
	model.objects.bulk_create(
		[
			model(
				**{
					related_manager.field.name: related_manager.instance,
					text_field: text,
					"order": order,
				}
			)
			for order, text in enumerate(texts)
		]
	)


class ZipImportMixin:
	"""Accepts either a ``.zip`` or a direct spreadsheet for import.

	**ZIP upload** (existing behaviour):
	The ZIP must contain one spreadsheet file (``.xlsx``, ``.xls``, or
	``.csv``) and an optional ``images/`` folder with image files
	referenced by filename in the spreadsheet's image columns.

	**Direct spreadsheet upload** (``.xlsx`` / ``.xls`` / ``.csv``):
	When no images are bundled, users can upload a spreadsheet directly.
	Image columns should then contain existing ``QuizAsset`` IDs instead
	of filenames.

	``skip_import_confirm`` is ``True`` so images only need to be
	loaded once (no two-step confirmation).
	"""

	_SPREADSHEET_EXTENSIONS = (".xlsx", ".xls", ".csv")

	skip_import_confirm = True

	def import_action(self, request, **kwargs):
		if request.method == "POST" and request.FILES.get("import_file"):
			import_file = request.FILES["import_file"]
			name_lower = import_file.name.lower()

			if name_lower.endswith(".zip"):
				raw = b"".join(import_file.chunks())
				try:
					xlsx_bytes = load_images_from_zip(raw)
				except (zipfile.BadZipFile, ValueError):
					logger.error(
						"Failed to extract ZIP import: %s",
						import_file.name,
						exc_info=True,
					)
					clear_image_store()
					raise
				logger.info("ZIP import extracted: %s", import_file.name)
				# Replace the uploaded file with the extracted spreadsheet.
				request.FILES["import_file"] = SimpleUploadedFile(
					name="import.xlsx",
					content=xlsx_bytes,
					content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
				)
			elif not any(
				name_lower.endswith(ext) for ext in self._SPREADSHEET_EXTENSIONS
			):
				from django.http import HttpResponseRedirect

				messages.error(
					request,
					"Only .zip, .xlsx, .xls, or .csv files are accepted. "
					"Upload a ZIP (with images) or a spreadsheet (with asset IDs).",
				)
				return HttpResponseRedirect(request.path)
		try:
			return super().import_action(request, **kwargs)
		finally:
			clear_image_store()

	def process_import(self, request, **kwargs):
		try:
			return super().process_import(request, **kwargs)
		finally:
			clear_image_store()


@admin.register(QuizCategory)
class QuizCategoryAdmin(admin.ModelAdmin):
	list_display = ["code", "name", "name_el", "order"]
	list_editable = ["name", "name_el", "order"]
	ordering = ["order", "code"]


@admin.register(MapArea)
class MapAreaAdmin(admin.ModelAdmin):
	"""Read-only: rows are generated from the GeoJSON the frontend draws, and a
	name typed by hand would simply never match one. Use ``sync_map_areas`` to
	bring the table in line after the map data changes.

	Registered mainly so the names are searchable — and so ``MapPointer``'s area
	picker has a permission-checked admin behind it.
	"""

	list_display = ["name", "level", "answer_count"]
	list_filter = ["level"]
	search_fields = ["name", "search_name"]
	ordering = ["level", "name"]

	def get_queryset(self, request):
		return super().get_queryset(request).prefetch_related("answers")

	def get_search_results(self, request, queryset, search_term):
		"""Match on the folded copy of the name, so "αθως" finds "Άθως".

		The admin's own ``search_fields`` does a plain ``icontains`` against what
		was typed; folding the term is what makes the stored ``search_name``
		useful. The area-options endpoint used to do this by scanning hundreds of
		names in Python on every keystroke.
		"""
		if not search_term:
			return super().get_search_results(request, queryset, search_term)
		return (
			queryset.filter(search_name__contains=fold_for_search(search_term)),
			False,
		)

	@admin.display(description="Used by answers")
	def answer_count(self, instance):
		return instance.answers.count()

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(QuizAsset)
class QuizAssetAdmin(ImportExportModelAdmin):
	list_display = [
		"id",
		"title",
		"image_preview",
		"image",
		"audio",
		"created_at",
		"updated_at",
	]
	search_fields = [
		"id",
		"title",
	]
	list_filter = ["created_at", "updated_at"]
	fieldsets = (
		(None, {"fields": ("title", "image", "audio")}),
		(
			"Other information",
			{
				"classes": ("collapse",),
				"fields": ("created_at", "updated_at"),
			},
		),
	)
	readonly_fields = ["created_at", "updated_at"]

	@admin.display(description="Image preview")
	def image_preview(self, obj):
		return get_admin_image_thumb_preview(obj.image)


class AbstractQuizAdmin(ZipImportMixin, ImportExportModelAdmin):
	skip_export_form = True

	# What the question itself is. Each subclass appends the fields specific to
	# its type; the prompt group is only added by the types that actually show a
	# prompt (``DragAndDrop`` does not).
	BASE_FIELDS = ("category", "test_number", "question_number", "is_active")
	PROMPT_FIELDS = ("prompt_text", "prompt_image", "prompt_audio")

	list_display = [
		"id",
		"category",
		"test_number",
		"question_number",
		"is_active",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	search_fields = [
		"id",
		"test_number",
		"question_number",
		# A real column now, so this is an indexable LIKE rather than a JSON path
		# that happened to work on SQLite's JSON1.
		"prompt_text",
	]
	list_filter = [
		"category",
		"test_number",
		"question_number",
		"is_active",
		"created_at",
		"updated_at",
	]
	autocomplete_fields = ["prompt_image", "prompt_audio"]
	fieldsets = (
		(None, {"fields": BASE_FIELDS}),
		("Prompt", {"fields": PROMPT_FIELDS}),
		(
			"Other information",
			{
				"classes": ("collapse",),
				"fields": ("created_at", "updated_at"),
			},
		),
	)
	readonly_fields = ["created_at", "updated_at"]

	@admin.display(description="Prompt preview", ordering="prompt_text")
	def prompt_preview(self, instance):
		image_thumb_preview = get_admin_image_thumb_preview(
			instance.prompt_image.image if instance.prompt_image else None
		)

		audio = instance.prompt_audio.audio if instance.prompt_audio else None
		audio_preview = (
			format_html('<audio controls src="{}"></audio>', audio.url) if audio else ""
		)

		if not instance.prompt_text and not image_thumb_preview and not audio_preview:
			return None

		return format_html_join(
			"",
			'<div style="display:flex;gap:10px;align-items:center;margin:10px 0;">'
			"  <span>{}</span>"
			"  <span>{}</span>"
			"  <span>{}</span>"
			"</div>",
			((instance.prompt_text, image_thumb_preview, audio_preview),),
		)

	def get_queryset(self, request):
		return (
			super().get_queryset(request).select_related("prompt_image", "prompt_audio")
		)


# ---------------------------------------------------------------------------
# Statement
# ---------------------------------------------------------------------------


class StatementChoiceFormSet(forms.BaseInlineFormSet):
	"""Where the "multiple choice needs a correct answer" rule is enforced on
	admin saves.

	The model cannot do it alone: the parent is saved before its inlines, so at
	``Statement.clean()`` time a new question has no choices yet. Same two-place
	split ``Listening`` has always used.
	"""

	def clean(self):
		super().clean()
		if any(self.errors):
			return

		rows = [
			form.cleaned_data
			for form in self.forms
			if form.cleaned_data and not form.cleaned_data.get("DELETE")
		]
		# An empty question is allowed: the choices can be added on a second pass.
		if not rows:
			return

		if self.instance.type == Statement.StatementType.MULTIPLE_CHOICE and not any(
			row.get("is_correct") for row in rows
		):
			raise forms.ValidationError(
				"Multiple-choice questions must have at least one correct choice."
			)


class StatementChoiceInline(admin.TabularInline):
	model = StatementChoice
	formset = StatementChoiceFormSet
	extra = 0
	fields = ["order", "text", "image", "is_correct"]
	autocomplete_fields = ["image"]
	verbose_name = "Choice"
	verbose_name_plural = "Choices"


@admin.register(Statement)
class StatementAdmin(AbstractQuizAdmin):
	resource_classes = [StatementResource]
	inlines = [StatementChoiceInline]
	list_display = [
		"id",
		"type",
		"category",
		"test_number",
		"question_number",
		"is_active",
		"prompt_preview",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	search_fields = AbstractQuizAdmin.search_fields + [
		# Choices are rows now, so searching their text finally works — this was
		# a standing TODO for as long as they lived in the JSON blob.
		"choices__text",
	]
	list_filter = ["type"] + AbstractQuizAdmin.list_filter
	autocomplete_fields = AbstractQuizAdmin.autocomplete_fields + ["listening", "part"]
	fieldsets = (
		(None, {"fields": ("type", *AbstractQuizAdmin.BASE_FIELDS)}),
		("Prompt", {"fields": AbstractQuizAdmin.PROMPT_FIELDS}),
		(
			"Listening question",
			{
				"description": (
					"Only for statements that are part of a listening question. "
					"Edit these from the Listening page instead."
				),
				"fields": ("listening", "part", "order"),
			},
		),
		AbstractQuizAdmin.fieldsets[-1],
	)

	def get_queryset(self, request):
		return super().get_queryset(request).prefetch_related("choices__image")

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		choices = list(instance.choices.all())

		if not choices:
			return None

		return format_html_join(
			"",
			'<div style="display:flex;gap:10px;align-items:center;margin:10px 0;">'
			'  <span style="width:20px">{}</span>'
			"  <span>{}</span>"
			"  <span>{}</span>"
			"</div>",
			(
				(
					"✅" if choice.is_correct else "◻️",
					choice.text,
					get_admin_image_thumb_preview(
						choice.image.image if choice.image else None
					),
				)
				for choice in choices
			),
		)


# ---------------------------------------------------------------------------
# Listening
# ---------------------------------------------------------------------------


def part_position_choices(part_count):
	"""Positions a question can be assigned to: always the two parts the exam has,
	plus any further ones the group already grew."""
	return [
		(position, f"Part {position}") for position in range(1, max(2, part_count) + 1)
	]


class ListeningQuestionForm(FixedCategoryFormMixin, forms.ModelForm):
	"""Picks the part by position rather than by row, so a question can be added
	in the same save as the part it belongs to — a part being created in that same
	save has no pk for a dropdown to point at yet.

	``ListeningAdmin.save_formset`` turns the position back into the ``part`` FK
	once the parts inline has been saved.

	A question asked about a clip is part of the listening section whatever
	subject the clip covers, so it is categorised as such and the picker is left
	off the inline.
	"""

	fixed_category = QuizCategory.LISTENING

	part_position = forms.TypedChoiceField(
		coerce=int,
		choices=part_position_choices(0),
		label="Part",
		help_text=(
			"Which part above this question belongs to, counting from the top. "
			"Parts added in this same save count too."
		),
	)

	class Meta:
		model = Statement
		fields = ["order", "type", "prompt_text", "is_active"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		part = self.instance.part if self.instance.part_id else None
		if part:
			self.fields["part_position"].initial = part.position


class ListeningQuestionFormSet(forms.BaseInlineFormSet):
	def clean(self):
		super().clean()
		if any(self.errors):
			return

		types = [
			form.cleaned_data["type"]
			for form in self.forms
			if form.cleaned_data and not form.cleaned_data.get("DELETE")
		]
		# An empty group is allowed so the clip can be created first and its
		# questions added on a second pass.
		if types:
			validate_listening_question_types(types)


class ListeningPartInline(admin.StackedInline):
	model = ListeningPart
	extra = 0
	fields = ["description"]
	verbose_name = "Part"
	verbose_name_plural = (
		"Parts, in order (shown as Μέρος Α, Μέρος Β, … — each with the "
		"description introducing it)"
	)


class ListeningQuestionInline(admin.StackedInline):
	"""The questions of a listening group, minus their choices.

	Choices are rows on ``Statement`` now, and Django has no nested inlines — so
	each question's choices are edited on its own page, reached by the link in
	``choices_preview``. Everything else about the question stays editable here.
	"""

	model = Statement
	fk_name = "listening"
	form = ListeningQuestionForm
	formset = ListeningQuestionFormSet
	extra = 0
	ordering = ["part_id", "order", "id"]
	fields = ["part_position", "order", "type", "prompt_text", "is_active"]
	readonly_fields = ["choices_preview"]
	verbose_name = "Question"
	verbose_name_plural = "Questions (1 True/False + N multiple choice)"

	def get_fields(self, request, obj=None):
		# The preview needs a saved row to link to, so it is only shown once the
		# question exists.
		return self.fields + ["choices_preview"]

	@admin.display(description="Choices")
	def choices_preview(self, instance):
		if not instance.pk:
			return "Save the question, then edit its choices on its own page."

		rows = format_html_join(
			"",
			"<div>{} {}</div>",
			(
				("✅" if choice.is_correct else "◻️", choice.text)
				for choice in instance.choices.all()
			),
		)
		link = format_html(
			'<a href="{}">Edit choices →</a>',
			f"/admin/quiz/statement/{instance.pk}/change/",
		)
		return format_html("{}<div style='margin-top:6px'>{}</div>", rows, link)

	def get_formset(self, request, obj=None, **kwargs):
		"""Offer one position per part of the group being edited. The field is
		copied first: its choices are per-group, but the declared field object is
		shared by every request."""
		formset = super().get_formset(request, obj, **kwargs)
		field = copy.deepcopy(formset.form.base_fields["part_position"])
		field.choices = part_position_choices(obj.parts.count() if obj else 0)
		formset.form.base_fields["part_position"] = field
		return formset


@admin.register(ListeningPart)
class ListeningPartAdmin(admin.ModelAdmin):
	"""Parts are edited inline on the listening question. This registration exists
	only so ``part`` can be an autocomplete field on ``StatementAdmin``: the
	autocomplete endpoint looks its target up in the admin registry and 404s
	unless that admin declares ``search_fields``. The page itself is hidden and
	read-only, so the inline stays the one way in.

	``has_view_permission`` is left alone — autocomplete permission-checks against
	it. None of this reaches ``ListeningPartInline``, whose permissions are
	checked on the inline class rather than here.
	"""

	search_fields = ["id", "description", "listening__id"]

	def get_model_perms(self, request):
		return {}

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False


class ListeningForm(FixedCategoryFormMixin, forms.ModelForm):
	"""Every clip belongs to the listening section, so the category is stamped on
	rather than picked."""

	fixed_category = QuizCategory.LISTENING

	class Meta:
		model = Listening
		fields = "__all__"


@admin.register(Listening)
class ListeningAdmin(admin.ModelAdmin):
	form = ListeningForm
	inlines = [ListeningPartInline, ListeningQuestionInline]
	list_display = [
		"id",
		"test_number",
		"question_number",
		"is_active",
		"audio_preview",
		"question_count",
		"max_plays",
		"created_at",
		"updated_at",
	]
	# Required by ``StatementAdmin.autocomplete_fields``.
	search_fields = ["id", "test_number", "question_number", "transcript"]
	list_filter = [
		"test_number",
		"question_number",
		"is_active",
		"created_at",
		"updated_at",
	]
	autocomplete_fields = ["audio"]
	fields = [
		"test_number",
		"question_number",
		"is_active",
		"audio",
		"max_plays",
		"transcript",
		"created_at",
		"updated_at",
	]
	readonly_fields = ["created_at", "updated_at"]

	def save_formset(self, request, form, formset, change):
		"""Point each saved question at the part whose position it picked.

		The parts inline comes first in ``inlines`` and so is saved first, which is
		what lets a part and its questions be created in the same save: by the time
		the questions are saved, the parts they refer to exist. A position with no
		part behind it grows the group an empty one, rather than leaving the
		question in no part at all and out of the exam.
		"""
		if formset.model is not Statement:
			super().save_formset(request, form, formset, change)
			return

		pending = formset.save(commit=False)
		for question_form in formset.forms:
			question = question_form.instance
			if question not in pending:
				continue
			position = question_form.cleaned_data["part_position"]
			question.part, created = ListeningPart.at_position(form.instance, position)
			if created:
				self.message_user(
					request,
					f"Part {position} did not exist yet — added it without a "
					f"description. Give it one below.",
					messages.WARNING,
				)
			question.save()

		for question in formset.deleted_objects:
			question.delete()
		formset.save_m2m()

	def get_queryset(self, request):
		return (
			super()
			.get_queryset(request)
			.select_related("audio")
			.prefetch_related("parts", "questions__choices")
		)

	@admin.display(description="Audio")
	def audio_preview(self, instance):
		url = instance.audio_url
		return format_html('<audio controls src="{}"></audio>', url) if url else None

	@admin.display(description="Questions")
	def question_count(self, instance):
		return instance.questions.count()


# ---------------------------------------------------------------------------
# Drag and drop
# ---------------------------------------------------------------------------


class DragAndDropValueInline(admin.TabularInline):
	model = DragAndDropValue
	extra = 0
	fields = ["side", "order", "text"]
	verbose_name = "Value"
	verbose_name_plural = "Values (assign each to its column)"


@admin.register(DragAndDrop)
class DragAndDropAdmin(AbstractQuizAdmin):
	resource_classes = [DragAndDropResource]
	inlines = [DragAndDropValueInline]
	# This type shows no prompt — its content is the two columns and nothing
	# else — so the prompt group is left off rather than offering fields that
	# would never reach the client.
	autocomplete_fields = []
	search_fields = ["id", "test_number", "question_number", "values__text"]
	fieldsets = (
		(None, {"fields": AbstractQuizAdmin.BASE_FIELDS}),
		("Columns", {"fields": ("left_title", "right_title")}),
		AbstractQuizAdmin.fieldsets[-1],
	)

	def get_queryset(self, request):
		# Skips AbstractQuizAdmin's prompt select_related: no prompt here.
		return admin.ModelAdmin.get_queryset(self, request).prefetch_related("values")

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		values = list(instance.values.all())

		def render_col(title, side):
			items_html = format_html_join(
				"",
				"<li>{}</li>",
				((v.text,) for v in values if v.side == side),
			)
			return format_html(
				"""
				<div style="
					flex: 1;
					padding: 12px;
					border: 1px solid #e6e6fa;
					border-radius: 8px;
				">
					<div style="font-weight: 600; margin-bottom: 8px;">{}</div>
					<ul style="margin: 0; padding-left: 18px;">{}</ul>
				</div>
				""",
				title,
				items_html,
			)

		return format_html(
			"""
			<div style="display:flex; gap: 12px; align-items: flex-start; max-width: 900px;">
				{} {}
			</div>
			""",
			render_col(instance.left_title, DragAndDropValue.Side.LEFT),
			render_col(instance.right_title, DragAndDropValue.Side.RIGHT),
		)


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


class MatchPairInline(admin.TabularInline):
	model = MatchPair
	extra = 0
	fields = ["order", "left_text", "left_image", "right_text", "right_image"]
	autocomplete_fields = ["left_image", "right_image"]
	verbose_name = "Pair"
	verbose_name_plural = "Pairs (each row is one correct match)"


@admin.register(Matching)
class MatchingAdmin(AbstractQuizAdmin):
	resource_classes = [MatchingResource]
	inlines = [MatchPairInline]
	autocomplete_fields = []
	search_fields = AbstractQuizAdmin.search_fields + [
		"pairs__left_text",
		"pairs__right_text",
	]
	fieldsets = (
		(None, {"fields": AbstractQuizAdmin.BASE_FIELDS}),
		("Prompt", {"fields": ("prompt_text",)}),
		("Columns", {"fields": ("left_title", "right_title")}),
		AbstractQuizAdmin.fieldsets[-1],
	)

	def get_queryset(self, request):
		return admin.ModelAdmin.get_queryset(self, request).prefetch_related(
			"pairs__left_image", "pairs__right_image"
		)

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		pairs = list(instance.pairs.all())

		def label(text, image):
			return text or (image.title or image.pk if image else "")

		def render_col(title, side, list_type="1"):
			items_html = format_html_join(
				"",
				"<li>{}</li>",
				(
					(
						label(pair.left_text, pair.left_image)
						if side == "left"
						else label(pair.right_text, pair.right_image),
					)
					for pair in pairs
				),
			)
			return format_html(
				"""
				<div style="
					flex: 1;
					padding: 12px;
					border: 1px solid #e6e6fa;
					border-radius: 8px;
				">
					<div style="font-weight: 600; margin-bottom: 8px;">{}</div>
					<ol type="{}" style="margin: 0; padding-left: 18px;">{}</ol>
				</div>
				""",
				title,
				list_type,
				items_html,
			)

		# The row *is* the pairing now, so this no longer has to search one column
		# for the other's matched_id.
		result_list_html = format_html_join(
			"",
			"<p><em>{} → {}</em></p>",
			(
				(
					label(pair.left_text, pair.left_image),
					label(pair.right_text, pair.right_image),
				)
				for pair in pairs
			),
		)

		return format_html(
			"""
			<div style="display:flex; gap: 12px; align-items: flex-start; max-width: 900px;">
				{} {}
			</div>
			<div style="margin-top: 10px;">
				{}
			</div>
			""",
			render_col(instance.left_title, "left"),
			render_col(instance.right_title, "right", list_type="A"),
			result_list_html,
		)


# ---------------------------------------------------------------------------
# Fill in the blank
# ---------------------------------------------------------------------------


class FillInTheBlankTextInline(admin.TabularInline):
	model = FillInTheBlankText
	extra = 0
	fields = ["order", "text"]
	verbose_name = "Sentence"
	verbose_name_plural = "Sentences (use <{{answer}}*> to mark a blank)"


class FillInTheBlankExtraChoiceInline(admin.TabularInline):
	model = FillInTheBlankExtraChoice
	extra = 0
	fields = ["order", "text"]
	verbose_name = "Extra choice"
	verbose_name_plural = (
		"Extra choices (decoys, only used when answers are shown as choices)"
	)


@admin.register(FillInTheBlank)
class FillInTheBlankAdmin(AbstractQuizAdmin):
	resource_classes = [FillInTheBlankResource]
	inlines = [FillInTheBlankTextInline, FillInTheBlankExtraChoiceInline]
	autocomplete_fields = ["prompt_image"]
	search_fields = ["id", "test_number", "question_number", "texts__text"]
	fieldsets = (
		(None, {"fields": AbstractQuizAdmin.BASE_FIELDS}),
		("Prompt", {"fields": ("prompt_image", "show_answers_as_choices")}),
		AbstractQuizAdmin.fieldsets[-1],
	)

	def get_queryset(self, request):
		return (
			admin.ModelAdmin.get_queryset(self, request)
			.select_related("prompt_image")
			.prefetch_related("texts")
		)

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		"""Each sentence with its blanks filled in, plus the answer key.

		Reads the model's own parse rather than re-implementing the markup rules
		here, which is what it used to do.
		"""

		def correct_of(part):
			correct = [c["text"] for c in part["choices"] if c["is_correct"]]
			return correct[0] if correct else "?"

		def render(parsed):
			out = []
			for part in parsed.parts:
				if not part["is_blank"]:
					out.append(format_html("{}", part["text"]))
					continue
				out.append(
					format_html(
						"<u><strong>{}</strong></u> ({})",
						correct_of(part),
						", ".join(c["text"] for c in part["choices"]),
					)
				)
			return mark_safe("".join(str(chunk) for chunk in out))

		try:
			parsed_texts = [row.parse() for row in instance.texts.all()]
		except ValidationError as error:
			# A changelist must still render when one row's markup is malformed.
			return format_html("<em>Invalid markup: {}</em>", "; ".join(error.messages))

		all_correct = [
			correct_of(part)
			for parsed in parsed_texts
			for part in parsed.parts
			if part["is_blank"]
		]

		rendered_html_list = format_html_join(
			"", "<p>{}</p>", ((render(parsed),) for parsed in parsed_texts)
		)

		return format_html(
			"""
			<div>
				<p><em>{}</em></p>
			</div>
			<div style="margin-top: 10px;">
				{}
			</div>
			""",
			", ".join(all_correct),
			rendered_html_list,
		)


# ---------------------------------------------------------------------------
# Open ended
# ---------------------------------------------------------------------------


class AnswerAlternativesForm(forms.ModelForm):
	"""Edits an answer group's alternatives as one-per-line text.

	``alternatives`` is not a model field — it stands in for the child rows,
	which are two levels below the question and so cannot be a nested inline.
	"""

	alternatives = LineListField(
		required=True,
		help_text="One spelling or phrasing per line. Any of them counts as correct.",
	)
	alternatives_model = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.instance.pk:
			self.fields["alternatives"].initial = [
				alt.text for alt in self.instance.alternatives.all()
			]

	def save(self, commit=True):
		answer = super().save(commit=commit)
		if commit:
			self._save_alternatives(answer)
		else:
			# The formset saves deferred rows itself; hook the child write onto it.
			original = getattr(answer, "save", None)

			def save_with_alternatives(*args, **kwargs):
				original(*args, **kwargs)
				self._save_alternatives(answer)

			answer.save = save_with_alternatives
		return answer

	def _save_alternatives(self, answer):
		sync_line_rows(answer.alternatives, self.cleaned_data["alternatives"])


class OpenEndedAnswerForm(AnswerAlternativesForm):
	class Meta:
		model = OpenEndedAnswer
		fields = ["order"]


class OpenEndedAnswerInline(admin.TabularInline):
	model = OpenEndedAnswer
	form = OpenEndedAnswerForm
	extra = 0
	verbose_name = "Answer"
	verbose_name_plural = "Answers"


@admin.register(OpenEnded)
class OpenEndedAdmin(AbstractQuizAdmin):
	resource_classes = [OpenEndedResource]
	inlines = [OpenEndedAnswerInline]
	autocomplete_fields = ["prompt_image"]
	list_display = [
		"id",
		"category",
		"is_active",
		"prompt_preview",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	search_fields = AbstractQuizAdmin.search_fields + [
		"answers__alternatives__text",
	]
	fieldsets = (
		(None, {"fields": AbstractQuizAdmin.BASE_FIELDS}),
		("Prompt", {"fields": ("prompt_text", "prompt_image")}),
		("Answers", {"fields": ("min_correct_answers",)}),
		AbstractQuizAdmin.fieldsets[-1],
	)

	def get_queryset(self, request):
		return (
			admin.ModelAdmin.get_queryset(self, request)
			.select_related("prompt_image")
			.prefetch_related("answers__alternatives")
		)

	@admin.display(description="Prompt", ordering="prompt_text")
	def prompt_preview(self, instance):
		image_thumb_preview = get_admin_image_thumb_preview(
			instance.prompt_image.image if instance.prompt_image else None
		)

		if not instance.prompt_text and not image_thumb_preview:
			return None

		return format_html_join(
			"",
			'<div style="display:flex;gap:10px;align-items:center;margin:10px 0;">'
			"  <span>{}</span>"
			"  <span>{}</span>"
			"</div>",
			((instance.prompt_text, image_thumb_preview),),
		)

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		answers = list(instance.answers.all())

		if not answers:
			return None

		# Reads the alternatives rows directly. The JSON version still looked for
		# a "text" key that migration 0003 had replaced, so every answer rendered
		# as an empty bullet.
		answers_html = format_html_join(
			"",
			'<li style="margin:4px 0;">{}</li>',
			((", ".join(alt.text for alt in a.alternatives.all()),) for a in answers),
		)

		return format_html(
			"""
			<div>
				<div style="margin-bottom:6px;">
					<strong>Min correct:</strong> {}
				</div>
				<ul style="margin:0; padding-left:18px;">{}</ul>
			</div>
			""",
			instance.min_correct_answers,
			answers_html,
		)


# ---------------------------------------------------------------------------
# Map pointer
# ---------------------------------------------------------------------------


class MapPointerAnswerForm(AnswerAlternativesForm):
	"""An answer plus the areas it may be placed on.

	The areas are a real queryset scoped to the question's map level, which is
	what replaced the JSON-schema enum: no import-time GeoJSON read, no client-side
	script rewriting a dropdown, and a foreign key that makes a renamed area
	findable instead of silently wrong.
	"""

	areas = forms.ModelMultipleChoiceField(
		queryset=MapArea.objects.none(),
		widget=FilteredSelectMultiple("areas", is_stacked=False),
		required=True,
		help_text=(
			"The answer counts as correct on any of the selected areas. Only areas "
			"of the question's map level are offered — change the level and save to "
			"switch lists."
		),
	)

	class Meta:
		model = MapPointerAnswer
		fields = ["order"]

	def __init__(self, *args, level=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.level = level or MapPointer._meta.get_field("level").default
		self.fields["areas"].queryset = MapArea.objects.filter(level=self.level)
		if self.instance.pk:
			self.fields["areas"].initial = [
				link.area_id for link in self.instance.areas.all()
			]

	def _save_alternatives(self, answer):
		super()._save_alternatives(answer)
		answer.areas.all().delete()
		MapPointerAnswerArea.objects.bulk_create(
			[
				MapPointerAnswerArea(answer=answer, area=area, order=order)
				for order, area in enumerate(self.cleaned_data["areas"])
			]
		)


class MapPointerAnswerInline(admin.StackedInline):
	model = MapPointerAnswer
	form = MapPointerAnswerForm
	extra = 0
	verbose_name = "Answer"
	verbose_name_plural = "Answers"

	@staticmethod
	def _level_for(request, obj):
		"""Which level's areas the picker should offer.

		On a bound submission it has to be the level that was just posted, not the
		saved one — otherwise picking a non-default level fails validation against
		the wrong list, which is the same trap the old JSON widget fell into.
		"""
		posted = request.POST.get("level")
		if posted:
			try:
				return int(posted)
			except (TypeError, ValueError):
				pass
		if obj:
			return obj.level
		return None

	def get_formset(self, request, obj=None, **kwargs):
		"""Scope the area picker to the level of the question being edited.

		On the add page there is no saved level yet, so the model default is used
		until the author picks one and saves. That is the whole of what the
		148-line ``map_pointer_level.js`` used to do client-side.
		"""
		formset = super().get_formset(request, obj, **kwargs)
		level = self._level_for(request, obj)

		class LevelBoundFormSet(formset):
			def _construct_form(self, i, **form_kwargs):
				form_kwargs["level"] = level
				return super()._construct_form(i, **form_kwargs)

			@property
			def empty_form(self):
				form = self.form(
					auto_id=self.auto_id,
					prefix=self.add_prefix("__prefix__"),
					empty_permitted=True,
					use_required_attribute=False,
					level=level,
					**self.get_form_kwargs(None),
				)
				self.add_fields(form, None)
				return form

		return LevelBoundFormSet


@admin.register(MapPointer)
class MapPointerAdmin(AbstractQuizAdmin):
	inlines = [MapPointerAnswerInline]
	autocomplete_fields = []
	list_display = [
		"id",
		"test_number",
		"question_number",
		"level",
		"is_active",
		"prompt_preview",
		"answer_preview",
		"created_at",
		"updated_at",
	]
	list_filter = ["level"] + without_category(AbstractQuizAdmin.list_filter)
	search_fields = AbstractQuizAdmin.search_fields + [
		"answers__alternatives__text",
		"answers__areas__area__name",
	]
	# Map questions are always geography ones, so the picker is left off and the
	# model default (GEOGRAPHY) stands.
	fieldsets = (
		(None, {"fields": ("level", *without_category(AbstractQuizAdmin.BASE_FIELDS))}),
		("Prompt", {"fields": ("prompt_text",)}),
		("Answers", {"fields": ("min_correct_answers", "show_answers")}),
		AbstractQuizAdmin.fieldsets[-1],
	)

	def get_queryset(self, request):
		return admin.ModelAdmin.get_queryset(self, request).prefetch_related(
			"answers__alternatives", "answers__areas__area"
		)

	@admin.display(description="Prompt", ordering="prompt_text")
	def prompt_preview(self, instance):
		return instance.prompt_text

	@admin.display(description="Answer")
	def answer_preview(self, instance):
		answers = list(instance.answers.all())
		if not answers:
			return None

		return format_html_join(
			"",
			'<div style="margin:4px 0;"><strong>{}</strong> → <code>{}</code></div>',
			(
				(
					", ".join(alt.text for alt in answer.alternatives.all()),
					" / ".join(link.area.name for link in answer.areas.all()),
				)
				for answer in answers
			),
		)
