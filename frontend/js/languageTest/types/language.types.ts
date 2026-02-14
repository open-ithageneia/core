export type MultipleChoiceQuestionType = {
	id: string
	type: string
	question: string
	options: Record<string, string>
	correctAnswer: string
}

export type TrueFalseQuestionType = {
	id: string
	type: "trueFalseNA"
	question: string
	correctAnswer: string
}

export type Question = {
	id: string
	type: string
	question: string
	options?: Record<string, string>
	correctAnswer: string
}

export type GradedAnswer = {
	id: string
	userAnswer: string | undefined
	correctAnswer: string
	correct: boolean
	hasSpellingErrors?: boolean
	type: string
}

export type EssayScores = {
	content: number
	coherence: number
	grammar: number
	vocabulary: number
	structure: number
}

export type EssayResult = {
	status: boolean
	scores: EssayScores
	total: number
	feedback: string
	modelAnswer: string
}
