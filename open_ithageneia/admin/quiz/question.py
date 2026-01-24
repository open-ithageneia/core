from typing import OrderedDict

from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from open_ithageneia.models.quiz import *
from open_ithageneia.models.shared import Semester


class QuizQuestionResource(resources.ModelResource):
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(QuizCategoryModel, field='name'), )

    type = fields.Field(
        column_name='type',
        attribute='type',
        widget=ForeignKeyWidget(QuizQuestionTypeModel, field='code'), )

    semester = fields.Field(
        column_name='semester',
        attribute="semester",
        widget=ForeignKeyWidget(Semester, field='id'),
    )

    class Meta:
        model = QuizQuestionModel
        fields = ( 'category', 'type', 'semester', 'number', 'context', 'min_correct_answers',
                   'are_sentences_continuous')
        exclude = ('id',)
        import_id_fields = ()
        skip_unchanged = False

    def before_import_row(self, row: OrderedDict, **kwargs):
        row["semester"] = Semester.objects.get(year=row["year"], half=row["half"]).id

    def after_save_instance(self, instance: QuizQuestionModel, row: OrderedDict, **kwargs):

        if instance.type.code == "TF" or instance.type.code == "MC":
            self.import_statement_answers(instance, row)
        elif instance.type.code == "REC":
            self.import_recall_answers(instance, row)
        elif instance.type.code == "CAT" or instance.type.code == "MAP" or instance.type.code == "GF":
            self.import_mapping_answers(instance, row)
        elif instance.type.code == "GFMC":
            self.import_fill_blank_answers(instance, row)

    @staticmethod
    def import_statement_answers(instance: QuizQuestionModel, row: OrderedDict):
        answer_cols = [k for k in row.keys() if k and k.lower().startswith("s_") and not k.lower().endswith("_correct")]

        for col in sorted(answer_cols):
            text = row[col]
            if not text:
                continue

            correct_col = f"{col}_correct"
            is_correct = row.get(correct_col, False)

            QuizQuestionItemModel.objects.create(
                question=instance,
                text=text,
                is_correct=bool(is_correct)
            )

    @staticmethod
    def import_recall_answers(instance: QuizQuestionModel, row: OrderedDict):
        answer_cols = [k for k in row.keys() if k and k.lower().startswith("r_")]

        for col in sorted(answer_cols):
            text = row[col]
            if not text:
                continue

            QuizQuestionItemModel.objects.create(
                question=instance,
                text=text,
            )

    @staticmethod
    def import_mapping_answers(instance: QuizQuestionModel, row: OrderedDict):
        first_group = MappingGroupModel.objects.create(
            question=instance,
            name=row.get('group_a_name', None),
            is_first=True
        )
        second_group = MappingGroupModel.objects.create(
            question=instance,
            name=row.get('group_b_name', None),
            is_first=False
        )

        first_group_answers = [k for k in row.keys() if k and k.lower().startswith("a_")]
        second_group_answers = [k for k in row.keys() if k and k.lower().startswith("b_")]
        for a, b in zip(first_group_answers, second_group_answers):
            a_text = row[a]
            b_text = row[b]
            first = QuizQuestionItemModel.objects.create(
                mapping_group=first_group,
                text=a_text,
                question=instance,
            )
            second = QuizQuestionItemModel.objects.create(
                mapping_group=second_group,
                text=b_text,
                question=instance,
            )

            MappingPairModel.objects.create(
                first=first,
                second=second,
            )

    @staticmethod
    def import_fill_blank_answers(instance: QuizQuestionModel, row: OrderedDict):
        NotImplemented()


@admin.register(QuizQuestionModel)
class QuizQuestionAdmin(ImportExportModelAdmin):
    resource_class = QuizQuestionResource
