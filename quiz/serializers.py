"""Serializers for the quiz types.

Each quiz type is stored relationally — a row plus child rows — but the client
receives a single ``content`` object per question, the same shape it has always
received. Assembling that object is this module's job: there is no separate
schema layer between the models and the wire.

``quiz/golden/wire_format.json`` records exactly what these emit. Run
``manage.py snapshot_wire_format --check`` after changing anything here.
"""

from rest_framework import serializers

from .models import (
	DragAndDrop,
	DragAndDropValue,
	FillInTheBlank,
	Listening,
	MapPointer,
	Matching,
	OpenEnded,
	QuizAsset,
	QuizCategory,
	Statement,
)


def _or_none(text):
	"""``""`` → ``None``.

	The columns are ``blank=True, default=""`` in the Django way, but the client
	has always been handed ``null`` for an absent prompt or title. No row has ever
	stored an empty string meaning something different from "not set", so the two
	are interchangeable going out.
	"""
	return text or None


def _image_url(asset):
	"""URL of an asset's image, or ``None``.

	Takes the already-loaded ``QuizAsset`` rather than an id, so a prefetch does
	the work — resolving by id ran one query per choice per question.
	"""
	if asset is not None and asset.image:
		return asset.image.url
	return None


def _audio_url(asset):
	if asset is not None and asset.audio:
		return asset.audio.url
	return None


class QuizContentSerializer(serializers.ModelSerializer):
	"""Base for the types that carry a ``content`` object.

	``content_prefetch`` names the relations ``get_content`` will walk. Nothing
	enforces it, but a list serialized without it is a query per question per
	relation — see ``QuizService.with_content``.
	"""

	content = serializers.SerializerMethodField()
	content_prefetch: tuple[str, ...] = ()

	def get_content(self, instance):
		raise NotImplementedError

	def _prompt(self, instance, text=True, image=True, audio=False):
		"""The prompt keys, for the types that show one. Which keys a type emits
		is part of its contract, so each says what it wants rather than taking a
		fixed set."""
		prompt = {}
		if text:
			prompt["prompt_text"] = _or_none(instance.prompt_text)
		if image:
			prompt["prompt_asset_url"] = _image_url(instance.prompt_image)
		if audio:
			prompt["prompt_audio_url"] = _audio_url(instance.prompt_audio)
		return prompt


class QuizAssetSerializer(serializers.ModelSerializer):
	class Meta:
		model = QuizAsset
		fields = ["id", "title", "image"]


class StatementSerializer(QuizContentSerializer):
	content_prefetch = ("prompt_image", "prompt_audio", "choices__image")

	class Meta:
		model = Statement
		fields = [
			"id",
			"category",
			"type",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]

	def get_content(self, instance):
		return {
			"choices": [
				{
					"is_correct": choice.is_correct,
					"text": _or_none(choice.text),
					"asset_url": _image_url(choice.image),
				}
				for choice in instance.choices.all()
			],
			**self._prompt(instance, audio=True),
		}


class ListeningSerializer(serializers.ModelSerializer):
	"""Serializes a listening question and its parts.

	The one type with no ``content`` object: its questions are plain ``Statement``
	rows and everything else about it is a column.
	"""

	audio_url = serializers.ReadOnlyField()
	parts = serializers.SerializerMethodField()

	class Meta:
		model = Listening
		fields = [
			"id",
			"category",
			"audio_url",
			"max_plays",
			"transcript",
			"parts",
			"is_active",
			"created_at",
			"updated_at",
		]

	def get_parts(self, obj):
		"""The sections the exam is split into, in order, each with its description
		and the questions that belong to it.

		Parts have no name of their own — the client labels them Α, Β, … by their
		position here, so the order matters. Parts with no questions are left out.
		Ordered explicitly rather than via a prefetch so the order holds however
		the serializer is called; a listening question has a handful of parts at
		most.
		"""
		parts = []
		for part in obj.parts.order_by("id"):
			questions = list(
				part.questions.order_by("order", "id").prefetch_related(
					*StatementSerializer.content_prefetch
				)
			)
			if not questions:
				continue
			parts.append(
				{
					"id": part.id,
					"description": part.description,
					"questions": StatementSerializer(questions, many=True).data,
				}
			)
		return parts


class DragAndDropSerializer(QuizContentSerializer):
	content_prefetch = ("values",)

	class Meta:
		model = DragAndDrop
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]

	def get_content(self, instance):
		"""A bare list of the two columns — this type has no prompt."""
		# One pass over the prefetched rows rather than two filtered queries, so
		# the prefetch is actually used.
		values = list(instance.values.all())
		return [
			{
				"title": _or_none(title),
				"values": [v.text for v in values if v.side == side],
			}
			for title, side in (
				(instance.left_title, DragAndDropValue.Side.LEFT),
				(instance.right_title, DragAndDropValue.Side.RIGHT),
			)
		]


class MatchingSerializer(QuizContentSerializer):
	content_prefetch = ("pairs__left_image", "pairs__right_image")

	class Meta:
		model = Matching
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]

	def get_content(self, instance):
		"""Rebuild the two columns from the pair rows.

		``id``/``matched_id`` are regenerated here rather than stored: with *n*
		pairs, left item *i* is ``id=i+1, matched_id=i+1+n`` and its partner is the
		mirror of that. That is the numbering the importer always synthesised, so
		the client sees exactly what it saw when this was a JSON blob.
		"""
		pairs = list(instance.pairs.all())
		count = len(pairs)

		left = [
			{
				"text": _or_none(pair.left_text),
				"asset_url": _image_url(pair.left_image),
				"id": index + 1,
				"matched_id": index + 1 + count,
			}
			for index, pair in enumerate(pairs)
		]
		right = [
			{
				"text": _or_none(pair.right_text),
				"asset_url": _image_url(pair.right_image),
				"id": index + 1 + count,
				"matched_id": index + 1,
			}
			for index, pair in enumerate(pairs)
		]

		return {
			**self._prompt(instance, image=False),
			"columns": [
				{"title": _or_none(instance.left_title), "items": left},
				{"title": _or_none(instance.right_title), "items": right},
			],
		}


class FillInTheBlankSerializer(QuizContentSerializer):
	content_prefetch = ("prompt_image", "texts", "extra_choices")

	class Meta:
		model = FillInTheBlank
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]

	def get_content(self, instance):
		# Parsed once and handed to both the parts and the word bank, since the
		# bank is derived from the same walk over the markup.
		parsed = [text.parse() for text in instance.texts.all()]

		return {
			"show_answers_as_choices": instance.show_answers_as_choices,
			"has_multiple_choices": any(text.has_multiple_choices for text in parsed),
			"prompt_instruction_choices": instance.instruction_choices(parsed),
			"texts": [{"parts": text.parts} for text in parsed],
			**self._prompt(instance, text=False),
		}


class OpenEndedSerializer(QuizContentSerializer):
	content_prefetch = ("prompt_image", "answers__alternatives")

	class Meta:
		model = OpenEnded
		fields = [
			"id",
			"category",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]

	def get_content(self, instance):
		return {
			"min_correct_answers": instance.min_correct_answers,
			"texts": [
				[alt.text for alt in answer.alternatives.all()]
				for answer in instance.answers.all()
			],
			**self._prompt(instance),
		}


class MapPointerSerializer(QuizContentSerializer):
	content_prefetch = ("answers__alternatives", "answers__areas__area")

	class Meta:
		model = MapPointer
		fields = [
			"id",
			"category",
			"level",
			"content",
			"is_active",
			"created_at",
			"updated_at",
		]

	def get_content(self, instance):
		texts = []
		for answer in instance.answers.all():
			group = {"alternatives": [alt.text for alt in answer.alternatives.all()]}
			# An answer with no areas omits the key rather than sending an empty
			# list, which is what the client has always been given.
			areas = [link.area.name for link in answer.areas.all()]
			if areas:
				group["areas"] = areas
			texts.append(group)

		return {
			"show_answers": instance.show_answers,
			"min_correct_answers": instance.min_correct_answers,
			"texts": texts,
			**self._prompt(instance, image=False),
		}


class ExerciseQuerySerializer(serializers.Serializer):
	category = serializers.CharField(default="", allow_blank=True)
	amount = serializers.ChoiceField(default=10, choices=[5, 10, 20])
	quiz_type = serializers.ChoiceField(
		default="",
		choices=[
			("", "All"),
			("Statement", "Statement"),
			("DragAndDrop", "DragAndDrop"),
			("FillInTheBlank", "FillInTheBlank"),
			("OpenEnded", "OpenEnded"),
			("Matching", "Matching"),
			("MapPointer", "MapPointer"),
			("Listening", "Listening"),
		],
	)

	def validate_category(self, value):
		if not value:
			return ""
		valid = set(QuizCategory.objects.values_list("code", flat=True))
		for cat in value.split(","):
			cat = cat.strip()
			if cat and cat not in valid:
				raise serializers.ValidationError(f"Invalid category: {cat}")
		return value
