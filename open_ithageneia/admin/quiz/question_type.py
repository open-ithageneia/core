from django.contrib import admin

from open_ithageneia.models.quiz import QuizQuestionTypeModel


@admin.register(QuizQuestionTypeModel)
class QuizQuestionTypeModelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "instructions",
    )
