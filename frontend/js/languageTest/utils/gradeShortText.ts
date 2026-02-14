import { simplifyLang } from "./simplifyLang"

type ShortTextQuestion = {
	id: string
	correctAnswer: string
	caseSensitive?: boolean
	trim?: boolean
	normalizeGreek?: boolean
}

export const isShortTextCorrect = (
	userAnswer: string | undefined,
	question: ShortTextQuestion,
) => {
	if (!userAnswer) return false

	let user = userAnswer
	let correct = question.correctAnswer

	if (question.trim !== false) {
		user = user.trim()
		correct = correct.trim()
	}

	if (!question.caseSensitive) {
		user = user.toLowerCase()
		correct = correct.toLowerCase()
	}

	if (question.normalizeGreek) {
		user = simplifyLang(user)
		correct = simplifyLang(correct)
	}

	return user === correct
}

export const gradeShortTextDetailed = (
	userAnswer: string | undefined,
	correctAnswer: string,
) => {
	if (!userAnswer) {
		return { correct: false, hasSpellingErrors: false }
	}

	const cleanUser = userAnswer.trim()
	const cleanCorrect = correctAnswer.trim()

	if (cleanUser === cleanCorrect) {
		return { correct: true, hasSpellingErrors: false }
	}

	const simplifiedUser = simplifyLang(cleanUser)
	const simplifiedCorrect = simplifyLang(cleanCorrect)

	if (simplifiedUser === simplifiedCorrect) {
		return { correct: true, hasSpellingErrors: true }
	}

	return { correct: false, hasSpellingErrors: false }
}
