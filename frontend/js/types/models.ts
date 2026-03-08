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

interface QuizChoice {
	text?: string
	asset_id?: number
	is_correct: boolean
}

interface TrueFalseContent {
	prompt_text?: string
	prompt_asset_id?: number
	choices: QuizChoice[]
}

interface MultipleChoiceContent {
	prompt_text?: string
	prompt_asset_id?: number
	choices: QuizChoice[]
}

export interface Statement extends TimeStamped, Activatable {
	id: number
	type: StatementType
	category: QuizCategory
	content: TrueFalseContent | MultipleChoiceContent
	exam_sessions: ExamSession[]
	exam_sessions_preview: string
}

interface DragAndDropColumn {
	title: string
	values: string[]
}

export type DragAndDropContent = [DragAndDropColumn, DragAndDropColumn]

export interface DragAndDrop extends TimeStamped, Activatable {
	id: number
	category: QuizCategory
	content: DragAndDropContent
	exam_sessions: ExamSession[]
	exam_sessions_preview: string
}

interface MatchingItem {
	id?: number
	matched_id?: number
	text: string
}

interface MatchingColumn {
	title: string
	items: MatchingItem[]
}

export type MatchingContent = [MatchingColumn, MatchingColumn]

export interface Matching extends TimeStamped, Activatable {
	id: number
	category: QuizCategory
	content: MatchingContent
	exam_sessions: ExamSession[]
	exam_sessions_preview: string
}

interface FillInTheBlankContent {
	prompt_asset_id?: number
	show_answers_as_choices: boolean
	texts: string[]
}

export interface FillInTheBlank extends TimeStamped, Activatable {
	id: number
	category: QuizCategory
	content: FillInTheBlankContent
	exam_sessions: ExamSession[]
	exam_sessions_preview: string
}

export interface Exam {
	true_false: [Statement]
	multiple_choice: [Statement]
	fill_in_the_blank: [FillInTheBlank]
	drag_and_drop: [DragAndDrop]
	matching: [Matching]
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
	quiz_type: string
}[]
