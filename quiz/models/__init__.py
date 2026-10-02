"""Quiz models, one module per quiz type with its content tables beside it.

Everything is re-exported here, so ``from quiz.models import X`` keeps working
and Django finds every model when it imports the app's ``models`` module.
Migrations also reference ``quiz.models.get_quiz_asset_upload_to`` by path.
"""

from .assets import QuizAsset, QuizCategory, get_quiz_asset_upload_to
from .base import AbstractQuiz, MinCorrectAnswersMixin, ModelABCMeta
from .drag_and_drop import DragAndDrop, DragAndDropValue
from .fill_in_the_blank import (
	FillInTheBlank,
	FillInTheBlankChoice,
	FillInTheBlankExtraChoice,
	FillInTheBlankPart,
	FillInTheBlankText,
)
from .listening import Listening, ListeningPart, validate_listening_question_types
from .map_area import MapArea, MapLevel, fold_for_search
from .map_pointer import (
	MapPointer,
	MapPointerAlternative,
	MapPointerAnswer,
	MapPointerAnswerArea,
)
from .matching import Matching, MatchPair
from .open_ended import OpenEnded, OpenEndedAlternative, OpenEndedAnswer
from .statement import Statement, StatementChoice
from .word_relation import WordRelation, WordRelationChoice, split_sentence

__all__ = [
	"AbstractQuiz",
	"DragAndDrop",
	"DragAndDropValue",
	"FillInTheBlank",
	"FillInTheBlankChoice",
	"FillInTheBlankExtraChoice",
	"FillInTheBlankPart",
	"FillInTheBlankText",
	"Listening",
	"ListeningPart",
	"MapArea",
	"MapLevel",
	"MapPointer",
	"MapPointerAlternative",
	"MapPointerAnswer",
	"MapPointerAnswerArea",
	"MatchPair",
	"Matching",
	"MinCorrectAnswersMixin",
	"ModelABCMeta",
	"OpenEnded",
	"OpenEndedAlternative",
	"OpenEndedAnswer",
	"QuizAsset",
	"QuizCategory",
	"Statement",
	"StatementChoice",
	"WordRelation",
	"WordRelationChoice",
	"fold_for_search",
	"get_quiz_asset_upload_to",
	"split_sentence",
	"validate_listening_question_types",
]
