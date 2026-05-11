import type { QuizCategory, StatementType } from "@/types/enums"

interface TimeStamped {
	created: string
	modified: string
}

interface Activatable {
	is_active: boolean
}

export interface ExamSession extends TimeStamped {
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
	exam_sessions_preview: string
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

export type MatchingContent = [MatchingColumn, MatchingColumn]

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

export interface Exam {
	true_false: [StatementModel]
	multiple_choice: [StatementModel]
	fill_in_the_blank: [FillInTheBlankModel]
	drag_and_drop: [DragAndDropModel]
	matching: [MatchingModel]
	open_ended: [OpenEndedModel]
}

export type TrainingData = {
	id: number
	category: QuizCategory
	content:
		| FillInTheBlankContent
		| TrueFalseContent
		| MultipleChoiceContent
		| MatchingContent
		| DragAndDropContent
		| OpenEndedContent
	quiz_type: string
}[]
