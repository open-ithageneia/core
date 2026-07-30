import type { MapLevel, QuizCategory, StatementType } from "@/types/enums"

interface TimeStamped {
	created_at: string
	updated_at: string
}

interface Activatable {
	is_active: boolean
}

export interface QuizAsset extends TimeStamped {
	id: number
	title: string
	image: string
}

interface QuizBase extends TimeStamped, Activatable {
	id: number
	category: QuizCategory
}

interface QuizChoice {
	text?: string
	asset_url?: string
	is_correct: boolean
}

interface TrueFalseContent {
	prompt_text?: string
	prompt_asset_url?: string
	prompt_audio_url?: string
	choices: QuizChoice[]
}

interface MultipleChoiceContent {
	prompt_text?: string
	prompt_asset_url?: string
	prompt_audio_url?: string
	choices: QuizChoice[]
}

export interface StatementModel extends QuizBase {
	type: StatementType
	content: TrueFalseContent | MultipleChoiceContent
}

/**
 * One section of a listening question. Parts are unnamed: their order in
 * `ListeningModel.parts` is what makes one Μέρος Α and the next Μέρος Β.
 */
export interface ListeningPartGroup {
	id: number
	/** Text introducing the part, shown above its questions. Empty when unset. */
	description: string
	/** The first part is usually the TRUE_FALSE statements, the second the MULTIPLE_CHOICE ones. */
	questions: StatementModel[]
}

/**
 * An audio comprehension question: one clip plus the statements and
 * multiple-choice questions asked about it, split into parts A and B. Unlike the
 * other quiz types this one has no `content` — its questions are plain
 * statements.
 */
export interface ListeningModel extends QuizBase {
	audio_url: string | null
	max_plays: number
	transcript: string
	/** Only parts that actually have questions are included. */
	parts: ListeningPartGroup[]
}

interface DragAndDropColumn {
	title: string
	values: string[]
}

export type DragAndDropContent = [DragAndDropColumn, DragAndDropColumn]

export interface DragAndDropModel extends QuizBase {
	content: DragAndDropContent
}

export interface MatchingItem {
	id?: number
	matched_id?: number
	text: string
	asset_url?: string
}

interface MatchingColumn {
	title: string
	items: MatchingItem[]
}

export interface MatchingContent {
	prompt_text?: string
	columns: [MatchingColumn, MatchingColumn]
}

export interface MatchingModel extends QuizBase {
	content: MatchingContent
}

export interface FillBlankChoice {
	text: string
	is_correct: boolean
}

export interface FillBlankTextPart {
	text: string
	is_blank: boolean
	choices?: FillBlankChoice[]
}

export interface FillBlankText {
	parts: FillBlankTextPart[]
}

export interface FillInTheBlankContent {
	prompt_asset_url?: string
	prompt_instruction_choices?: string[]
	has_multiple_choices: boolean
	texts: FillBlankText[]
}

export interface FillInTheBlankModel extends QuizBase {
	content: FillInTheBlankContent
}

export interface OpenEndedContent {
	min_correct_answers: number
	is_ans_num_shown: boolean
	prompt_text?: string
	prompt_asset_url?: string
	texts: string[][]
}

export interface OpenEndedModel extends QuizBase {
	content: OpenEndedContent
}

export interface MapPointerTextGroup {
	alternatives: string[]
	/**
	 * Every area this answer may be placed on — placing it on any one of them
	 * counts as correct (e.g. a river crossing several prefectures).
	 */
	areas?: string[]
}

export interface MapPointerContent {
	prompt_text: string
	min_correct_answers: number
	show_answers: boolean
	texts: MapPointerTextGroup[]
}

export interface MapPointerModel extends QuizBase {
	level: MapLevel
	content: MapPointerContent
}

export type QuizDataItem =
	| (StatementModel & { quiz_type: "Statement" })
	| (DragAndDropModel & { quiz_type: "DragAndDrop" })
	| (MatchingModel & { quiz_type: "Matching" })
	| (FillInTheBlankModel & { quiz_type: "FillInTheBlank" })
	| (OpenEndedModel & { quiz_type: "OpenEnded" })
	| (MapPointerModel & { quiz_type: "MapPointer" })
	| (ListeningModel & { quiz_type: "Listening" })

export type QuizData = QuizDataItem[]
