// core\frontend\js\trueFalse-alkis\core-transfer\hooks\useCoreFullGrading.tsx

import type {
	CoreAnswer,
	CoreGradedAnswer,
	GradeAllResult,
} from "../types/client.types"
import type { Statement } from "../types/models"

export const useCoreFullGrading = () => {
	// MULTIPLE CHOICE GRADING
	const gradeMultiple = (
		question: Statement,
		userAnswer: CoreAnswer | undefined,
	): CoreGradedAnswer => {
		if (question.type !== "MULTIPLE_CHOICE") {
			throw new Error("Wrong type")
		}

		const content = question.content

		// 👉 νέο σύστημα: πρέπει να είναι type 'single'
		if (!userAnswer || userAnswer.type !== "single") {
			return {
				id: question.id,
				userAnswer,
				correctAnswer: -1,
				correct: false,
				type: "MULTIPLE_CHOICE",
			}
		}

		// έχουμε ένα arr με [ { **, is_correct: false }, { **, is_correct: true } ]
		// βρίσκουμε σε ποιο index είναι η σωστή απάντηση στο ORIGINAL array
		const correctOriginalIndex = content.choices.findIndex(
			(choice) => choice.is_correct,
		)

		// βρίσκουμε σε ποια θέση εμφανίστηκε μετά το shuffle
		// order: UI θέση → original index
		const correctIndexInShuffled =
			userAnswer.order.indexOf(correctOriginalIndex)

		// συγκρίνουμε με αυτό που πάτησε ο user (index στο UI)
		const isCorrect = userAnswer.index === correctIndexInShuffled

		return {
			id: question.id,
			userAnswer,
			correctAnswer: correctOriginalIndex, // (κρατάμε και το correctAnswer για UI feedback)
			correct: isCorrect, // boolean σωστό/λάθος
			type: "MULTIPLE_CHOICE",
		}
	}

	// TRUE / FALSE GRADING
	const gradeTrueFalse = (
		question: Statement,
		userAnswer: CoreAnswer | undefined,
	): CoreGradedAnswer => {
		const content = question.content

		// =========================
		// CASE 1: MULTI TRUE/FALSE
		// =========================
		// 👉 κάθε choice είναι statement
		// 👉 userAnswer.values = { index: true/false }
		if (userAnswer?.type === "multi_tf") {
			// ελέγχουμε ΟΛΑ τα statements
			const allCorrect = content.choices.every((choice, index) => {
				const userVal = userAnswer.values[index]

				// σύγκριση:
				// user επέλεξε true/false === is_correct
				return userVal === choice.is_correct
			})

			return {
				id: question.id,
				userAnswer,
				correctAnswer: -1, // δεν έχει νόημα εδώ (πολλα answers)
				correct: allCorrect, // ALL OR NOTHING
				type: "TRUE_FALSE",
			}
		}

		// =========================
		// CASE 2: SIMPLE TRUE/FALSE
		// =========================
		// 👉 fallback αν έχουμε μόνο 1 σωστή επιλογή
		if (userAnswer?.type === "single") {
			const correctIndex = content.choices.findIndex((c) => c.is_correct)

			const isCorrect = userAnswer.index === correctIndex

			return {
				id: question.id,
				userAnswer,
				correctAnswer: correctIndex,
				correct: isCorrect,
				type: "TRUE_FALSE",
			}
		}

		// =========================
		// CASE 3: NO ANSWER
		// =========================
		return {
			id: question.id,
			userAnswer,
			correctAnswer: -1,
			correct: false,
			type: "TRUE_FALSE",
		}
	}

	// =========================
	// MAIN GRADING LOOP
	// =========================
	const gradeAll = (
		questions: Statement[],
		answers: Record<number, CoreAnswer>,
	): GradeAllResult => {
		let correct = 0
		const results: CoreGradedAnswer[] = []

		for (const question of questions) {
			// φέρνουμε την απάντηση απο το map answers (key = question.id)
			const userAnswer = answers[question.id]
			let result: CoreGradedAnswer

			switch (question.type) {
				case "MULTIPLE_CHOICE":
					result = gradeMultiple(question, userAnswer)
					break

				case "TRUE_FALSE":
					result = gradeTrueFalse(question, userAnswer)
					break

				default:
					throw new Error(`Unsupported type: ${question.type}`)
			}

			// αν σωστό → increment score
			if (result.correct) correct++

			// push στο results array (για UI feedback)
			results.push(result)
		}

		return {
			results,
			score: correct, // συνολικό score
		}
	}

	return { gradeAll }
}
