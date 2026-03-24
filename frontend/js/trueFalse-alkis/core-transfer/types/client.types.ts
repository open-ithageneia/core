export type CoreAnswer =
	| { type: "single"; index: number; order: number[] }
	| { type: "multi_tf"; values: Record<number, boolean> }

export type CoreGradedAnswer = {
	id: number
	userAnswer: CoreAnswer | undefined
	correctAnswer: number
	correct: boolean
	type: "TRUE_FALSE" | "MULTIPLE_CHOICE"
}

export type GradeAllResult = {
	results: CoreGradedAnswer[]
	score: number
}
