from django.contrib import admin

from open_ithageneia.models.quiz import QuizCategoryModel


@admin.register(QuizCategoryModel)
class QuizCategoryModelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
    search_fields = ("name",)
