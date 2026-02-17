// frontend\src\test-full\types\Full.types.ts

export type QuestionCategory = "γεωγραφία" | "πολιτισμός" | "θεσμοί" | "γλώσσα"

export type QuestionMediaItem = {
	id: string // πχ "1", "2", "A"
	type: "image" // αργότερα μπορεί να γίνει union
	src: string
	alt?: string
	caption?: string
}

export type FullQuestionBase = {
	id: string
	category: QuestionCategory
	media?: QuestionMediaItem[]
}

export type FullMultipleChoiceQuestion = FullQuestionBase & {
	type: "multipleChoice"
	question: string
	options: Record<string, string>
	correctAnswer: string
}

export type FullShortTextQuestion = FullQuestionBase & {
	type: "shortText"
	multipleBlanks: true
	question: string
	correctAnswer: string[]
}

export type FullMatchingQuestion = FullQuestionBase & {
	type: "matching"
	question: string
	columnAHeader?: string
	columnBHeader?: string
	columnA: { key: string; label: string }[]
	columnB: { key: string; label: string }[]
	correctAnswer: Record<string, string>
}

export type FullMultiSelectQuestion = FullQuestionBase & {
	type: "multiSelect"
	question: string
	minSelections: number
	maxSelections: number
	options: string[]
	correctAnswer: string[]
}

export type FullListInputQuestion = FullQuestionBase & {
	type: "listInput"
	question: string
	minItems: number
	maxItems: number
	correctAnswer: string[]
}

export type FullTrueFalseGroupQuestion = FullQuestionBase & {
	type: "trueFalseGroup"
	question: string
	statements: {
		key: string
		text: string
	}[]
	correctAnswer: Record<string, "T" | "F">
}

export type FullCategorizationQuestion = FullQuestionBase & {
	type: "categorization"
	question: string
	categories: {
		key: string
		label: string
	}[]
	items: string[]
	correctAnswer: Record<string, string[]> // categoryKey → items[]
}

export type MapPoint = {
	x: number // ποσοστό X (0–100)
	y: number // ποσοστό Y (0–100)
	label: string // κείμενο (προς το παρόν δεν βαθμολογείται)
}

export type GeoMapPointsQuestion = FullQuestionBase & {
	type: "mapPoints"
	question: string // όχι "ερώτηση"
	rules: {
		map: true
		maxPoints: number
		tolerancePct?: number
		expectsSubset?: boolean
		minItems?: number
		maxItems?: number
	}
	canonicalAnswer: {
		type: "points"
		points: {
			x: number
			y: number
			label: string
			aliases?: string[]
		}[]
	}
}

export type FullWordMatchingQuestion = FullQuestionBase & {
	type: "wordMatching"
	question: string
	wordBank: Record<string, string>
	textTemplate: string
	correctAnswer: Record<string, string>
	hasExtraOption?: boolean
}

export type FullOpenTextQuestion = FullQuestionBase & {
	type: "openText"
	question: string
	maxWords: number
	correctAnswer: string
}

export type FullQuestion =
	| FullMultipleChoiceQuestion
	| FullShortTextQuestion
	| FullMatchingQuestion
	| FullMultiSelectQuestion
	| FullListInputQuestion
	| FullTrueFalseGroupQuestion
	| FullCategorizationQuestion
	| GeoMapPointsQuestion
	| FullWordMatchingQuestion
	| FullOpenTextQuestion

export type FullAnswer =
	| string
	| string[]
	| Record<string, string>
	| MapPoint[]
	| MapPoint[]

export type GradedPoint = MapPoint & {
	correct: boolean
	labelCorrect: boolean
	hasSpellingErrors: boolean
}

export type LabelCheckResult = {
	correct: boolean
	hasSpellingErrors: boolean
}

export type FullGradedAnswer = {
	id: string
	userAnswer?: FullAnswer
	correctAnswer: unknown
	correct: boolean
	hasSpellingErrors?: boolean
	type: FullQuestion["type"]
	mapGradedPoints?: GradedPoint[]
	mapReviewPoints?: MapPoint[]

	openTextScores?: {
		content: number
		coverage: number
		language: number
		wordLimit: number
		total: number
	}
}
