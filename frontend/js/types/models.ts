import type { MapLevel, QuizCategory, StatementType } from "@/types/enums"

interface TimeStamped {
	created_at: string
	updated_at: string
}

interface Activatable {
	is_active: boolean
}

export interface ExamSession {
	id: number
	year: number
	month: number
	month_display: string
}

export interface QuizAsset extends TimeStamped {
	id: number
	title: string
	image: string
}

interface QuizBase extends TimeStamped, Activatable {
	id: number
	exam_sessions: ExamSession[]
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
	choices: QuizChoice[]
}

interface MultipleChoiceContent {
	prompt_text?: string
	prompt_asset_url?: string
	choices: QuizChoice[]
}

export interface StatementModel extends QuizBase {
	type: StatementType
	content: TrueFalseContent | MultipleChoiceContent
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
	area?: string
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

export type QuizData = QuizDataItem[]
