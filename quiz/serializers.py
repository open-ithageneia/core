"""Assembly of the ``content`` object each quiz type sends to the client.

This is the contract. ``frontend/js/types/models.ts`` is written against the
output of ``get_content()`` below, so a change here is a change to the client's
input whether or not one was intended. ``quiz/test_wire_format.py`` is what
proves a change didn't happen: it runs a corpus of content shapes through the
real migration and compares the result against the pre-refactor serializer.

Every serializer declares ``content_prefetch``: the related rows its
``get_content()`` walks. ``QuizService.with_content`` applies them, so the
prefetching lives next to the code that needs it instead of at each call site.
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


def image_url(asset):
	return asset.image_url if asset else None


def audio_url(asset):
	return asset.audio_url if asset else None


def text_or_none(value):
	"""A text column as the wire format has always carried it.

	These fields were JSON keys before they were columns, and an unset one came
	back as ``null`` — most visibly on ``Matching.prompt_text``, which is null on
	every row. A column cannot be absent, so empty stands in for unset and is
	reported the same way. The one behaviour this does not preserve is a value
	deliberately stored as an empty string, which now reports as null too; both
	are falsy to the client, and the original JSON is still on the row.
	"""
	return value or None


class QuizAssetSerializer(serializers.ModelSerializer):
	class Meta:
		model = QuizAsset
		fields = ["id", "title", "image"]


class StatementSerializer(serializers.ModelSerializer):
	content = serializers.SerializerMethodField()

	content_prefetch = ("choices__image", "prompt_image", "prompt_audio")

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

	def get_content(self, obj):
		return {
			"choices": [
				{
					"is_correct": choice.is_correct,
					"text": text_or_none(choice.text),
					"asset_url": image_url(choice.image),
				}
				for choice in obj.choices.all()
			],
			"prompt_text": text_or_none(obj.prompt_text),
			"prompt_asset_url": image_url(obj.prompt_image),
			"prompt_audio_url": audio_url(obj.prompt_audio),
		}


class ListeningSerializer(serializers.ModelSerializer):
	"""Serializes a listening question and its parts.

	This type has no ``content`` of its own — its questions are plain statements,
	so the client receives them under ``parts`` instead.
	"""

	audio_url = serializers.ReadOnlyField()
	parts = serializers.SerializerMethodField()

	content_prefetch = (
		"parts__questions__choices__image",
		"parts__questions__prompt_image",
		"parts__questions__prompt_audio",
	)

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
		"""The sections the exam is split into, in order, each with its
		description and the questions that belong to it.

		Parts have no name of their own — the client labels them Α, Β, … by their
		position here, so the order matters. Parts with no questions are left
		out.
		"""
		parts = []
		for part in obj.parts.all():
			questions = list(part.questions.all())
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


class DragAndDropSerializer(serializers.ModelSerializer):
	content = serializers.SerializerMethodField()

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

	def get_content(self, obj):
		# A bare two-element list, one entry per column — the shape the client's
		# `DragAndDropContent` tuple type is written against.
		values = list(obj.values.all())
		return [
			{
				"title": obj.left_title,
				"values": [
					value.text
					for value in values
					if value.side == DragAndDropValue.Side.LEFT
				],
			},
			{
				"title": obj.right_title,
				"values": [
					value.text
					for value in values
					if value.side == DragAndDropValue.Side.RIGHT
				],
			},
		]


class MatchingSerializer(serializers.ModelSerializer):
	content = serializers.SerializerMethodField()

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

	def get_content(self, obj):
		# ``id``/``matched_id`` are regenerated from the row order rather than
		# stored: a pair row already *is* the pairing, and these numbers only ever
		# existed so the client could link one column's item to the other's. Left
		# item i gets id i+1 and points at i+1+n, which is what the importer
		# synthesised from the pair index before the rows existed.
		left_sequence = list(obj.pairs.all())
		total = len(left_sequence)
		# The right column is ordered on its own, so that a question whose right
		# column is shuffled does not come back sorted into the answer.
		right_sequence = sorted(
			left_sequence, key=lambda pair: (pair.right_order, pair.order, pair.pk)
		)
		left_position = {pair.pk: index for index, pair in enumerate(left_sequence)}
		right_position = {pair.pk: index for index, pair in enumerate(right_sequence)}

		return {
			"prompt_text": text_or_none(obj.prompt_text),
			"columns": [
				{
					"title": text_or_none(obj.left_title),
					"items": [
						{
							"text": text_or_none(pair.left_text),
							"asset_url": image_url(pair.left_image),
							"id": index + 1,
							"matched_id": right_position[pair.pk] + 1 + total,
						}
						for index, pair in enumerate(left_sequence)
					],
				},
				{
					"title": text_or_none(obj.right_title),
					"items": [
						{
							"text": text_or_none(pair.right_text),
							"asset_url": image_url(pair.right_image),
							"id": index + 1 + total,
							"matched_id": left_position[pair.pk] + 1,
						}
						for index, pair in enumerate(right_sequence)
					],
				},
			],
		}


class FillInTheBlankSerializer(serializers.ModelSerializer):
	content = serializers.SerializerMethodField()

	content_prefetch = ("texts__parts__choices", "extra_choices", "prompt_image")

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

	def get_content(self, obj):
		# The parts are rows now, derived from the authored sentence when it is
		# saved, so this only has to shape them — no regex at request time.
		texts = list(obj.texts.all())
		return {
			"show_answers_as_choices": obj.show_answers_as_choices,
			"has_multiple_choices": any(text.has_multiple_choices for text in texts),
			"prompt_instruction_choices": obj.instruction_choices(),
			"texts": [
				{"parts": [self._part(part) for part in text.parts.all()]}
				for text in texts
			],
			"prompt_asset_url": image_url(obj.prompt_image),
		}

	@staticmethod
	def _part(part):
		# A blank sends no text: revealing the answer is the client's decision,
		# made from the choices.
		shaped = {
			"text": None if part.is_blank else part.text,
			"is_blank": part.is_blank,
		}
		if part.is_blank:
			shaped["choices"] = [
				{"text": choice.text, "is_correct": choice.is_correct}
				for choice in part.choices.all()
			]
		return shaped


class OpenEndedSerializer(serializers.ModelSerializer):
	content = serializers.SerializerMethodField()

	content_prefetch = ("answers__alternatives", "prompt_image")

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

	def get_content(self, obj):
		return {
			"min_correct_answers": obj.min_correct_answers,
			"prompt_text": text_or_none(obj.prompt_text),
			"texts": [
				[alternative.text for alternative in answer.alternatives.all()]
				for answer in obj.answers.all()
			],
			"prompt_asset_url": image_url(obj.prompt_image),
		}


class MapPointerSerializer(serializers.ModelSerializer):
	content = serializers.SerializerMethodField()

	content_prefetch = ("answers__alternatives", "answers__area_links__area")

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

	def get_content(self, obj):
		texts = []
		for answer in obj.answers.all():
			group = {
				"alternatives": [
					alternative.text for alternative in answer.alternatives.all()
				]
			}
			# ``areas`` is omitted rather than sent empty when an answer has none.
			areas = [link.area.name for link in answer.area_links.all()]
			if areas:
				group["areas"] = areas
			texts.append(group)

		return {
			"show_answers": obj.show_answers,
			"min_correct_answers": obj.min_correct_answers,
			"prompt_text": text_or_none(obj.prompt_text),
			"texts": texts,
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
