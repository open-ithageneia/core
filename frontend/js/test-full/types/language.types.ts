import type { FullQuestion } from "./Full.types"

export type LanguageFullTestType = {
	id: string
	category: "γλώσσα"
	type: "readingTest"
	title: string
	prompt: string
	text: string
	active?: boolean
	parts: {
		A: {
			type: "comprehension"
			instructions: string
			questions: FullQuestion[]
		}
		B: {
			type: "grammar"
			instructionsMultipleChoice?: string
			instructionsShortText?: string
			questions: FullQuestion[]
		}
		C: {
			type: "essay"
			instructions: string
			question: string
			minWords: number
			maxWords: number
			evaluation: {
				method: string
				responseFormat: string
				maxScore: number
				criteria: string[]
			}
		}
	}
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
