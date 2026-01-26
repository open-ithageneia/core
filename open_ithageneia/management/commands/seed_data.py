from django.core.management.base import BaseCommand

from open_ithageneia.models import *
from django.db import transaction


class Command(BaseCommand):
    help = "Seed database with initial production data"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.seed_categories()
        self.seed_semester()

        self.seed_sample_data()

    @staticmethod
    def seed_categories():
        categories = [
            QuizCategoryModel(name="ΓΕΩΓΡΑΦΙΑ"),
            QuizCategoryModel(name="ΠΟΛΙΤΙΣΜΟΣ"),
            QuizCategoryModel(name="ΙΣΤΟΡΙΑ"),
            QuizCategoryModel(name="ΠΟΛΙΤΙΚΟΙ ΘΕΣΜΟΙ"),
        ]

        for row in categories:
            QuizCategoryModel.objects.get_or_create(
                name=row.name,
            )

    @staticmethod
    def seed_semester():
        Semester.objects.get_or_create(year=2026, half=Semester.SemesterHalf.First)

        Semester.objects.get_or_create(year=2026, half=Semester.SemesterHalf.Second)

    def seed_sample_data(self):
        semester = Semester.objects.get(year=2026, half=Semester.SemesterHalf.First)

        geography = QuizCategoryModel.objects.get(name="ΓΕΩΓΡΑΦΙΑ")
        history = QuizCategoryModel.objects.get(name="ΙΣΤΟΡΙΑ")
        culture = QuizCategoryModel.objects.get(name="ΠΟΛΙΤΙΣΜΟΣ")
        institution = QuizCategoryModel.objects.get(name="ΠΟΛΙΤΙΚΟΙ ΘΕΣΜΟΙ")

        self.add_tf_sample(semester, geography, 1)
        self.add_mc_sample(semester, geography, 2)
        self.add_rec_sample(semester, history, 3)
        self.add_map_sample(semester, history, 4)
        self.add_cat_sample(semester, history, 5)
        self.add_gf_sample(semester, culture, 6)
        self.add_gfmc_sample(semester, culture, 8)

    @staticmethod
    def add_tf_sample(semester, category, number):
        q, _ = QuizTrueFalseQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
        )

        mc_answers = [
            ("Η Ελληνική Επανάσταση έγινε το 1821", True),
            ("Η Ελληνική Επανάσταση έγινε το 1820", False),
            ("Η Ελληνική Επανάσταση έγινε το 1819", False),
            ("Η Ελληνική Επανάσταση έγινε το 1818", False),
        ]

        for text, is_correct in mc_answers:
            QuizTrueFalseItem.objects.get_or_create(
                question=q, text=text, is_correct=is_correct
            )

    @staticmethod
    def add_mc_sample(semester, category, number):
        q, _ = QuizMultipleChoiceQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "context": "Πότε έγινε η Ελληνική Επανάσταση;",
            },
        )

        mc_answers = [
            ("1821", True),
            ("1830", False),
            ("1940", False),
            ("1912", False),
        ]

        for text, is_correct in mc_answers:
            QuizMultipleChoiceItem.objects.get_or_create(
                question=q, text=text, is_correct=is_correct
            )

    @staticmethod
    def add_rec_sample(semester, category, number):
        q, _ = QuizRecallQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "context": "4 πολεις της Ελλαδας;",
                "min_correct_answers": 4,
            },
        )

        rec_answers = [
            "Αθήνα",
            "Πατρα",
            "Θεσσαλονικη",
            "Χανια",
            "Τριπολη",
        ]

        for text in rec_answers:
            QuizRecallItem.objects.get_or_create(
                question=q,
                text=text,
            )

    @staticmethod
    def add_map_sample(semester, category, number):
        q, _ = QuizMappingQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "context": "Αντιστοιχίστε τις χώρες με τις πρωτεύουσές τους.",
            },
        )

        greece = QuizMappingItem.objects.get_or_create(
            question=q, column_name="Χώρες", text="Ελλάδα"
        )[0]

        france = QuizMappingItem.objects.get_or_create(
            question=q, column_name="Χώρες", text="Γαλλία"
        )[0]

        athens = QuizMappingItem.objects.get_or_create(
            question=q,
            column_name="Πρωτεύουσες",
            text="Αθήνα",
            pair=greece,
        )[0]
        greece.pair = athens

        paris = QuizMappingItem.objects.get_or_create(
            question=q,
            column_name="Πρωτεύουσες",
            text="Παρίσι",
            pair=france,
        )[0]

        france.pair = paris

    # ΓΕΩΓΡΦΙΑ ΘΕΜΑ 46
    @staticmethod
    def add_cat_sample(semester, category, number):
        q, _ = QuizCategorizeQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "context": "Αντιστοιχίστε τις χώρες με τις πρωτεύουσές τους.",
            },
        )

        land = QuizCategoryGroup.objects.get_or_create(
            question=q,
            text="Ηπειρωτική Ελλάδα",
        )[0]
        sea = QuizCategoryGroup.objects.get_or_create(
            question=q,
            text="Νησιωτική Ελλάδα",
        )[0]

        _ = QuizCategoryItem.objects.get_or_create(group=land, text="Αλεξανδρούπολη")[0]

        _ = QuizCategoryItem.objects.get_or_create(group=sea, text="Σίφνος")[0]

        _ = QuizCategoryItem.objects.get_or_create(group=land, text="Πύργος")[0]

    @staticmethod
    def add_gf_sample(semester, category, number):
        q, _ = QuizGapFillQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
            },
        )

        hatzidakis_blank = QuizGap.objects.get_or_create(
            question=q,
            text="Ο _ συνέθεσε τη μουσική στο τραγούδι: «Τα παιδιά του Πειραιά» που έγινε πολύ γνωστό με την ερμηνεία της Μελίνας Μερκούρη.",
        )[0]

        _ = QuizGapItem.objects.get_or_create(
            gap=hatzidakis_blank, text=" Μάνος Χατζηδάκι"
        )[0]

        hatzidakis_blank.pair = hatzidakis_blank

        reboutsika_blank = QuizGap.objects.get_or_create(
            question=q,
            text="Η _ συνέθεσε τη μουσική για την κινηματογραφική ταινία: «Πολίτικη Κουζίνα»",
        )[0]

        _ = QuizGapItem.objects.get_or_create(
            gap=reboutsika_blank, text="Ευανθία Ρεμπούτσικα"
        )[0]

    @staticmethod
    def add_gfmc_sample(semester, category, number):
        q, _ = QuizGapFillMultipleChoiceQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
            },
        )

        blank_1 = QuizGapMultipleChoice.objects.get_or_create(
            question=q,
            text="Στις ανασκαφές των _ εντοπίσθηκε η χρυσή προσωπίδα της φωτογραφίας,",
        )[0]

        _ = QuizGapChoiceItem.objects.get_or_create(
            gap=blank_1, text="Μυκηνών", is_correct=True
        )[0]

        _ = QuizGapChoiceItem.objects.get_or_create(
            gap=blank_1,
            text="Δελφών",
        )[0]

        blank_2 = QuizGapMultipleChoice.objects.get_or_create(
            question=q,
            text="η οποία πιστεύεται ότι απεικονίζει τον _",
        )[0]

        _ = QuizGapChoiceItem.objects.get_or_create(gap=blank_2, text="Όμηρο")[0]

        _ = QuizGapChoiceItem.objects.get_or_create(
            gap=blank_2, text="Αγαμέμνονα", is_correct=True
        )[0]
