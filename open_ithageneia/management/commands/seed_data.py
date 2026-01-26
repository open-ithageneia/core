from django.core.management.base import BaseCommand

from open_ithageneia.models import (
    QuizQuestionTypeModel,
    QuizCategoryModel,
    Semester,
    QuizQuestionItemModel,
    QuizQuestionModel,
    ItemGroupModel,
    ItemPairModel,
)
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
        self.add_gf_2_sample(semester, institution, gf_type, 7)
        self.add_gfmc_sample(semester, culture, gfmc_type, 8)

    @staticmethod
    def add_tf_sample(semester, category, q_type, number):
        q, _ = QuizQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
            },
        )

        mc_answers = [
            ("Η Ελληνική Επανάσταση έγινε το 1821", True),
            ("Η Ελληνική Επανάσταση έγινε το 1820", False),
            ("Η Ελληνική Επανάσταση έγινε το 1819", False),
            ("Η Ελληνική Επανάσταση έγινε το 1818", False),
        ]

        for text, is_correct in mc_answers:
            QuizQuestionItemModel.objects.get_or_create(
                question=q, text=text, defaults={"is_correct": is_correct}
            )

    @staticmethod
    def add_mc_sample(semester, category, q_type, number):
        q, _ = QuizQuestionModel.objects.get_or_create(
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
            QuizQuestionItemModel.objects.get_or_create(
                question=q, text=text, defaults={"is_correct": is_correct}
            )

    @staticmethod
    def add_rec_sample(semester, category, q_type, number):
        q, _ = QuizQuestionModel.objects.get_or_create(
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
            QuizQuestionItemModel.objects.get_or_create(
                question=q,
                text=text,
            )

    @staticmethod
    def add_map_sample(semester, category, q_type, number):
        q, _ = QuizQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
                "context": "Αντιστοιχίστε τις χώρες με τις πρωτεύουσές τους.",
            },
        )

        # Mapping groups
        group_countries = ItemGroupModel.objects.get_or_create(
            question=q,
            is_first=True,
            type=ItemGroupModel.GroupType.Choices,
            defaults={"name": "Χώρες"},
        )[0]

        group_capitals = ItemGroupModel.objects.get_or_create(
            question=q,
            is_first=False,
            type=ItemGroupModel.GroupType.Choices,
            defaults={"name": "Πρωτεύουσες"},
        )[0]

        # First column (countries)
        greece = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_countries, text="Ελλάδα"
        )[0]

        france = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_countries, text="Γαλλία"
        )[0]

        # Second column (capitals)
        athens = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_capitals, text="Αθήνα"
        )[0]

        paris = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_capitals, text="Παρίσι"
        )[0]

        # Mapping pairs
        ItemPairModel.objects.get_or_create(first=greece, second=athens)
        ItemPairModel.objects.get_or_create(first=france, second=paris)

    # ΓΕΩΓΡΦΙΑ ΘΕΜΑ 46
    @staticmethod
    def add_cat_sample(semester, category, q_type, number):
        q, _ = QuizQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
                "context": "Αντιστοιχίστε τις χώρες με τις πρωτεύουσές τους.",
            },
        )

        group_categories = ItemGroupModel.objects.get_or_create(
            question=q,
            type=ItemGroupModel.GroupType.Categories,
            is_first=True,
        )[0]

        group_areas = ItemGroupModel.objects.get_or_create(
            question=q,
            type=ItemGroupModel.GroupType.Choices,
            is_first=False,
        )[0]

        alexandroupoli = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_areas, text="Αλεξανδρούπολη"
        )[0]

        sifnos = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_areas, text="Σίφνος"
        )[0]

        pyrgos = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_areas, text="Πύργος"
        )[0]

        land = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_categories, text="Ηπειρωτική Ελλάδα"
        )[0]

        sea = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_categories, text="Νησιωτική Ελλάδα"
        )[0]

        ItemPairModel.objects.get_or_create(first=alexandroupoli, second=land)
        ItemPairModel.objects.get_or_create(first=pyrgos, second=land)
        ItemPairModel.objects.get_or_create(first=sifnos, second=sea)

    @staticmethod
    def add_gf_sample(semester, category, q_type, number):
        q, _ = QuizQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
            },
        )

        group_choices = ItemGroupModel.objects.get_or_create(
            question=q,
            type=ItemGroupModel.GroupType.Choices,
        )[0]

        group_blanks = ItemGroupModel.objects.get_or_create(
            question=q,
            type=ItemGroupModel.GroupType.Blanks,
        )[0]

        hatzidakis = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_choices, text=" Μάνος Χατζηδάκι"
        )[0]

        reboutsika = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_choices, text="Ευανθία Ρεμπούτσικα"
        )[0]

        hatzidakis_blank = QuizQuestionItemModel.objects.get_or_create(
            question=q,
            item_group=group_blanks,
            text="Ο _ συνέθεσε τη μουσική στο τραγούδι: «Τα παιδιά του Πειραιά» που έγινε πολύ γνωστό με την ερμηνεία της Μελίνας Μερκούρη.",
        )[0]

        reboutsika_blank = QuizQuestionItemModel.objects.get_or_create(
            question=q,
            item_group=group_blanks,
            text="Η _ συνέθεσε τη μουσική για την κινηματογραφική ταινία: «Πολίτικη Κουζίνα»",
        )[0]

        ItemPairModel.objects.get_or_create(first=hatzidakis, second=hatzidakis_blank)
        ItemPairModel.objects.get_or_create(first=reboutsika, second=reboutsika_blank)

    # Not all answers should be used example: 5 answers -  4 blanks
    @staticmethod
    def add_gf_2_sample(semester, category, q_type, number):
        q, _ = QuizQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
                "are_sentences_continuous": True,
            },
        )

        group_answers = ItemGroupModel.objects.get_or_create(
            question=q,
            type=ItemGroupModel.GroupType.Choices,
        )[0]

        group_blanks = ItemGroupModel.objects.get_or_create(
            question=q,
            type=ItemGroupModel.GroupType.Blanks,
        )[0]

        ans1 = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_answers, text="πέντε"
        )[0]

        ans2 = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_answers, text="ελληνική καταγωγή"
        )[0]

        ans3 = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_answers, text="έξι"
        )[0]

        ans4 = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_answers, text="την ιδιότητα του Έλληνα πολίτη"
        )[0]

        _ = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_answers, text="random word"
        )[0]

        blank_1 = QuizQuestionItemModel.objects.get_or_create(
            question=q,
            item_group=group_blanks,
            text="Για να εκλεγεί κάποιος Πρόεδρος της Δημοκρατίας, θα πρέπει να έχει _",
        )[0]
        blank_2 = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=group_blanks, text="για τουλάχιστον _ χρόνια"
        )[0]
        blank_3 = QuizQuestionItemModel.objects.get_or_create(
            question=q,
            item_group=group_blanks,
            text="Επίσης, θα πρέπει να έχει από πατέρα ή μητέρα _, να είναι τουλάχιστον 40 ετών και να έχει τη νόμιμη ικανότητα του εκλέγειν.",
        )[0]
        blank_4 = QuizQuestionItemModel.objects.get_or_create(
            question=q,
            item_group=group_blanks,
            text="Η διαδικασία εκλογής νέου Προέδρου της Δημοκρατίας, σε περίπτωση που ο εν ενεργεία Πρόεδρος αδυνατεί να ασκήσει τα καθήκοντά του για πάνω από 30 ημέρες, σε καμία περίπτωση δεν μπορεί να καθυστερήσει περισσότερο από _ συνολικά μήνες, αφότου άρχισε η διαδικασία αναπλήρωσής του.",
        )[0]

        ItemPairModel.objects.get_or_create(first=ans1, second=blank_2)
        ItemPairModel.objects.get_or_create(first=ans2, second=blank_3)
        ItemPairModel.objects.get_or_create(first=ans3, second=blank_4)
        ItemPairModel.objects.get_or_create(first=ans4, second=blank_1)

    @staticmethod
    def add_gfmc_sample(semester, category, q_type, number):
        q, _ = QuizQuestionModel.objects.get_or_create(
            semester=semester,
            category=category,
            number=number,
            defaults={
                "type": q_type,
                "are_sentences_continuous": True,
            },
        )

        blanks = ItemGroupModel.objects.get_or_create(
            question=q,
            type=ItemGroupModel.GroupType.Blanks,
        )[0]

        blank_1 = QuizQuestionItemModel.objects.get_or_create(
            question=q,
            item_group=blanks,
            text="Στις ανασκαφές των _ εντοπίσθηκε η χρυσή προσωπίδα της φωτογραφίας,",
        )[0]

        choices_1 = ItemGroupModel.objects.get_or_create(
            question=q,
            type=ItemGroupModel.GroupType.Choices,
        )[0]

        choice_1 = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=choices_1, linked_item=blank_1, text="Μυκηνών"
        )[0]

        _ = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=choices_1, linked_item=blank_1, text="Δελφών"
        )[0]

        ItemPairModel.objects.get_or_create(first=choice_1, second=blank_1)

        choices_2 = ItemGroupModel.objects.get_or_create(
            question=q,
            type=ItemGroupModel.GroupType.Choices,
        )[0]

        blank_2 = QuizQuestionItemModel.objects.get_or_create(
            question=q,
            item_group=choices_2,
            text="η οποία πιστεύεται ότι απεικονίζει τον _",
        )[0]

        _ = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=choices_2, linked_item=blank_2, text="Όμηρο"
        )[0]

        choice_2 = QuizQuestionItemModel.objects.get_or_create(
            question=q, item_group=choices_2, linked_item=blank_2, text="Αγαμέμνονα"
        )[0]

        ItemPairModel.objects.get_or_create(first=choice_2, second=blank_2)
