from django.core.management.base import BaseCommand

from open_ithageneia.models import *
from django.db import transaction


class Command(BaseCommand):
    help = "Seed database with initial production data"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.seed_categories()
        self.seed_question_types()
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
    def seed_question_types():
        categories = [
            QuizQuestionTypeModel(
                code="TF",
                name="Σ/Λ",
                instructions="Γράψτε στο τετράδιό σας τον αριθμό του θέματος και τον αριθμό της κάθε πρότασης σημειώνοντας Σ, αν η πρόταση που σας δίνεται παρακάτω είναι σωστή, ή Λ, αν είναι λάθος.",
            ),
            QuizQuestionTypeModel(
                code="MC",
                name="ΠΟΛΛΑΠΛΗΣ ΕΠΙΛΟΓΗΣ",
                instructions="Γράψτε στο τετράδιό σας τον αριθμό του θέματος και δίπλα τη σωστή απάντηση σημειώνοντας το αντίστοιχο γράμμα (Α ή Β ή Γ ή Δ).",
            ),
            QuizQuestionTypeModel(
                code="MAP",
                name="ΑΝΤΙΣΤΟΙΧΙΣΗ",
                instructions="Γράψτε στο τετράδιό σας τον αριθμό του θέματος και να αντιστοιχίσετε τους όρους της στήλης Ι με τους όρους της στήλης ΙΙ σημειώνοντας τον αριθμό της στήλης Ι και δίπλα το γράμμα από τη στήλη ΙΙ που ταιριάζει.",
            ),
            QuizQuestionTypeModel(
                code="GF",
                name="ΣΥΜΠΛΗΡΩΣΗ ΚΕΝΩΝ",
                instructions="Γράψτε στο τετράδιό σας τον αριθμό του θέματος και τον αριθμό που αντιστοιχεί σε κάθε κενό, σημειώνοντας δίπλα τη λέξη ή τη φράση που ταιριάζει, επιλέγοντας από τις παρακάτω",
            ),
            QuizQuestionTypeModel(
                code="GFMC",
                name="ΣΥΜΠΛΗΡΩΣΗ ΚΕΝΩΝ ΜΕ ΕΠΙΛΟΓΕΣ",
                instructions="Γράψτε στο τετράδιό σας τον αριθμό του θέματος και τον αριθμό που αντιστοιχεί σε κάθε κενό, σημειώνοντας δίπλα τη λέξη ή τη φράση που ταιριάζει, επιλέγοντας από τις παρακάτω",
            ),
            QuizQuestionTypeModel(
                code="CAT",
                name="ΚΑΤΗΓΟΡΙΟΠΟΙΣΗ",
                instructions="Γράψτε στο τετράδιό σας τον αριθμό του θέματος και να αντιστοιχίσετε τους όρους της στήλης Ι με τους όρους της στήλης ΙΙ σημειώνοντας τον αριθμό της στήλης Ι και δίπλα το γράμμα από τη στήλη ΙΙ που ταιριάζει.",
            ),
            QuizQuestionTypeModel(
                code="REC",
                name="ΜΝΗΜΗΣ",
                instructions="Γράψτε στο τετράδιό σας τον αριθμό του θέματος και",
            ),
        ]

        for row in categories:
            QuizQuestionTypeModel.objects.get_or_create(
                name=row.name,
                code=row.code,
                instructions=row.instructions,
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

        tf_type = QuizQuestionTypeModel.objects.get(code="TF")
        mc_type = QuizQuestionTypeModel.objects.get(code="MC")
        rec_type = QuizQuestionTypeModel.objects.get(code="REC")
        map_type = QuizQuestionTypeModel.objects.get(code="MAP")
        cat_type = QuizQuestionTypeModel.objects.get(code="CAT")
        gf_type = QuizQuestionTypeModel.objects.get(code="GF")
        gfmc_type = QuizQuestionTypeModel.objects.get(code="GFMC")

        self.add_tf_sample(semester, geography, tf_type, 1)
        self.add_mc_sample(semester, geography, mc_type, 2)
        self.add_rec_sample(semester, history, map_type, 3)
        self.add_map_sample(semester, history, rec_type, 4)
        self.add_cat_sample(semester, history, cat_type, 5)
        self.add_gf_sample(semester, culture, gf_type, 6)
        self.add_gfmc_sample(semester, culture, gfmc_type, 8)

    @staticmethod
    def add_tf_sample(semester, category, q_type, number):
        q, _ = QuizTrueFalseQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            type=q_type,
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
    def add_mc_sample(semester, category, q_type, number):
        q, _ = QuizMultipleChoiceQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
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
    def add_rec_sample(semester, category, q_type, number):
        q, _ = QuizRecallQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
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
    def add_map_sample(semester, category, q_type, number):
        q, _ = QuizMappingQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
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
    def add_cat_sample(semester, category, q_type, number):
        q, _ = QuizCategorizeQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
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
    def add_gf_sample(semester, category, q_type, number):
        q, _ = QuizGapFillQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
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
    def add_gfmc_sample(semester, category, q_type, number):
        q, _ = QuizGapFillMultipleChoiceQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
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
