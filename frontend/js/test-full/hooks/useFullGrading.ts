// frontend\src\test-full\hooks\useFullGrading.ts
/*
όλα τα grading functions επιστρέφουν τουλάχιστον:
{
  id: q.id,
  userAnswer,
  correctAnswer: ...,
  correct: boolean,
  type: q.type
}
και μερικά προσθέτουν extra:
hasSpellingErrors (shortText, listInput)
mapGradedPoints, mapReviewPoints (mapPoints)
openTextScores (openText)
*/

import axios from "axios"
import { urlOpenText } from "../constants/constants"
import type {
	FullAnswer,
	FullCategorizationQuestion,
	FullGradedAnswer,
	FullListInputQuestion,
	FullMatchingQuestion,
	FullMultipleChoiceQuestion,
	FullMultiSelectQuestion,
	FullOpenTextQuestion,
	FullQuestion,
	FullShortTextQuestion,
	FullTrueFalseGroupQuestion,
	FullTrueFalseNAQuestion,
	FullWordMatchingQuestion,
	GeoMapPointsQuestion,
	MapPoint,
} from "../types/Full.types"
import { buildReviewPoints, gradePoints } from "../utils/geoGrading"
import { expandOptionalParts, simplifyLang } from "../utils/simplifyLang"

type GradeAllResult = {
	results: FullGradedAnswer[]
	score: number
}

export const useFullGrading = () => {
	// 🖖 multipleChoice grading
	//  -------------------------
	// value schema: "A"  όπου value = το key της επιλογής (πχ "A", "B", "C", "D")
	const gradeMultipleChoice = (
		q: FullMultipleChoiceQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		// συγκρίνει τα δύο string
		const isCorrect = userAnswer === q.correctAnswer

		return {
			id: q.id,
			userAnswer,
			correctAnswer: q.correctAnswer,
			correct: isCorrect,
			type: q.type,
		}
	}

	// 🎉shortText grading
	// -------------------
	// value schema: Αν multipleBlanks = false: "Καποδίστριας" Αν multipleBlanks = true: ["Φίλιππος Β΄", "Κωνσταντίνος ΙΑ΄ Παλαιολόγος", ...]
	const gradeShortText = (
		q: FullShortTextQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		// η απάντηση μπορεί να είναι string ή string[]. To κάνουμε string[] πάντα
		const correctParts = Array.isArray(q.correctAnswer)
			? q.correctAnswer
			: [q.correctAnswer]

		// το ίδιο για την απάντηση του μαθητή
		const userParts: string[] =
			Array.isArray(userAnswer) &&
			userAnswer.every((item) => typeof item === "string")
				? userAnswer
				: typeof userAnswer === "string"
					? [userAnswer]
					: []

		let allCorrect = true
		let hasSpellingErrors = false

		// για κάθε κενο __
		correctParts.forEach((correctPart, index) => {
			const userPart = userParts[index]

			// Αν δεν έβαλε τίποτα
			if (!userPart) {
				allCorrect = false
				return
			}

			// Θέλουμε: ασφαλή (μετα)κίνηση → να θεωρείται ίδιο με ασφαλή μετακίνηση αλλα και με ασφαλή κίνηση. Και θα (του) αποσπάσεις → ίδιο με θα του αποσπάσεις αλλα και θα αποσπάσεις
			const expanded = expandOptionalParts(correctPart)

			let partMatched = false

			for (const variant of expanded) {
				// κάνουμε δύο ελέγχους simplifiedMatch και exactMatch αν και τα δύο τοτε σωστό, αν μόνο το simplified τότε σωστό με ορθογραφικά.
				const exactMatch = userPart.trim() === variant.trim()
				// simplifyLang: "Καλημέρα"→"kalimera"
				const simplifiedMatch = simplifyLang(userPart) === simplifyLang(variant)

				if (exactMatch) {
					partMatched = true
					break
				}

				if (!exactMatch && simplifiedMatch) {
					partMatched = true
					hasSpellingErrors = true
					break
				}
			}

			if (!partMatched) {
				allCorrect = false
			}
		})

		return {
			id: q.id,
			userAnswer,
			correctAnswer: q.correctAnswer,
			correct: allCorrect,
			hasSpellingErrors,
			type: q.type,
		}
	}

	// 💥 matching grading
	//  -------------------
	// value schema: { "1": "C", "2": "A" } όπου key = columnA.key και value = columnB.key
	const gradeMatching = (
		q: FullMatchingQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		// Type narrowing. Επειδή FullAnswer είναι union (string | string[] | object | MapPoint[] κλπ), πρέπει να βεβαιωθούμε ότι εδώ είναι object.
		const userMap =
			userAnswer && typeof userAnswer === "object" && !Array.isArray(userAnswer)
				? userAnswer
				: {}

		const correctMap = q.correctAnswer

		// Για κάθε σωστό key: ελέγχει αν ο user έβαλε το ίδιο value.
		// χρειαζόμαστε Object γιατί δεν είναι απλό Arr
		const allCorrect = Object.keys(correctMap).every(
			(key) => userMap[key] === correctMap[key],
		)

		return {
			id: q.id,
			userAnswer,
			correctAnswer: correctMap,
			correct: allCorrect,
			type: q.type,
		}
	}

	// 💣 multiSelect grading
	// ----------------------
	// value schema: ["B", "C"] όπου κάθε στοιχείο του array είναι option key.
	const gradeMultiSelect = (
		q: FullMultiSelectQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		// Type narrowing, multiSelect περιμένει string[]
		const userSelections: string[] =
			Array.isArray(userAnswer) &&
			userAnswer.every((item) => typeof item === "string")
				? userAnswer
				: []

		const correctOptions = q.correctAnswer

		// Μετρά πόσα από αυτά που διάλεξε ο χρήστης υπάρχουν μέσα στις σωστές επιλογές.
		const correctCount = userSelections.filter((opt) =>
			correctOptions.includes(opt),
		).length

		// Ο χρήστης πρέπει να διαλέξει ακριβώς maxSelections Και όλα αυτά να είναι σωστά
		const allCorrect =
			userSelections.length === q.maxSelections &&
			correctCount === userSelections.length

		return {
			id: q.id,
			userAnswer,
			correctAnswer: correctOptions,
			correct: allCorrect,
			type: q.type,
		}
	}

	// 🐥 listInput grading
	//  --------------------
	// value schema: ["Αττικής", "Κρήτης", "", ""] Array σταθερού μήκους (maxItems) Κάθε index αντιστοιχεί σε μία αριθμημένη γραμμή απάντησης.
	// Πάντα array μήκους maxItems, Κάποια indexes μπορεί να είναι "", Η θέση δεν παίζει ρόλο στο grading
	const gradeListInput = (
		q: FullListInputQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		// Type narrowing. listInput επίσης περιμένει string[]
		const userParts: string[] =
			Array.isArray(userAnswer) &&
			userAnswer.every((item) => typeof item === "string")
				? userAnswer
				: []

		const cleaned = userParts.map((a) => a.trim()).filter(Boolean)

		// διαθέσιμες σωστές απαντήσεις
		const remaining = [...q.correctAnswer]

		let hasSpellingErrors = false
		let matchedCount = 0

		for (const ans of cleaned) {
			// 1) exact match
			const exactIndex = remaining.findIndex((c) => c.trim() === ans)

			if (exactIndex !== -1) {
				matchedCount++
				remaining.splice(exactIndex, 1)
				continue
			}

			// 2) simplified match (ορθογραφική ανοχή)
			const simplifiedIndex = remaining.findIndex(
				(c) => simplifyLang(c) === simplifyLang(ans),
			)

			if (simplifiedIndex !== -1) {
				matchedCount++
				hasSpellingErrors = true
				remaining.splice(simplifiedIndex, 1)
			}
		}

		// ελέγχουμε αν ο αριθμός των απαντήσεων είναι εντός ορίων
		const meetsCount =
			cleaned.length >= q.minItems && cleaned.length <= q.maxItems

		const allCorrect = meetsCount && matchedCount === q.maxItems

		return {
			id: q.id,
			userAnswer,
			correctAnswer: q.correctAnswer,
			correct: allCorrect,
			hasSpellingErrors: allCorrect ? hasSpellingErrors : false,
			type: q.type,
		}
	}

	// ✅ trueFalseGroup grading
	//  ------------------------
	// value schema: { "1": "T", "2": "F", "3": "T" } όπου key = statement.key
	const gradeTrueFalseGroup = (
		q: FullTrueFalseGroupQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		const userMap =
			userAnswer && typeof userAnswer === "object" && !Array.isArray(userAnswer)
				? (userAnswer as Record<string, "T" | "F">)
				: {}

		const correctMap = q.correctAnswer

		const allCorrect = Object.keys(correctMap).every(
			(key) => userMap[key] === correctMap[key],
		)

		return {
			id: q.id,
			userAnswer,
			correctAnswer: correctMap,
			correct: allCorrect,
			type: q.type,
		}
	}

	// 😶trueFalseNA grading
	// ---------------------
	// value schema: "T" | "F" | "NA" Απλό string union. Δεν είναι object όπως στο trueFalseGroup.
	const gradeTrueFalseNA = (
		q: FullTrueFalseNAQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		const isCorrect = userAnswer === q.correctAnswer

		return {
			id: q.id,
			userAnswer,
			correctAnswer: q.correctAnswer,
			correct: isCorrect,
			type: q.type,
		}
	}

	// 😺 categorization grading
	// -------------------------
	// value schema: { "Κερκίνη": "II", "Αλιάκμονας": "I" }
	const gradeCategorization = (
		q: FullCategorizationQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		const userMap =
			userAnswer && typeof userAnswer === "object" && !Array.isArray(userAnswer)
				? (userAnswer as Record<string, string>)
				: {}

		const correctMap = q.correctAnswer

		const allCorrect = Object.entries(correctMap).every(
			([categoryKey, items]) =>
				items.every((item) => userMap[item] === categoryKey),
		)

		return {
			id: q.id,
			userAnswer,
			correctAnswer: correctMap,
			correct: allCorrect,
			type: q.type,
		}
	}

	// helper: ελέγχει αν είναι MapPoint[]
	const isMapPointArray = (value: unknown): value is MapPoint[] => {
		return (
			Array.isArray(value) &&
			value.every(
				(v) =>
					typeof v === "object" &&
					v !== null &&
					"x" in v &&
					"y" in v &&
					"label" in v,
			)
		)
	}

	// 🌏 mapPoints grading
	// ---------------------
	const gradeMapPoints = (
		q: GeoMapPointsQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		const userPoints = isMapPointArray(userAnswer) ? userAnswer : []

		const tolerance = q.rules?.tolerancePct ?? 3.5

		// core γεωμετρικό grading
		const graded = gradePoints(userPoints, q.canonicalAnswer.points, tolerance)

		// buildReviewPoints:
		// δημιουργεί merged view (user + canonical)
		const reviewPoints = buildReviewPoints(
			graded,
			q.canonicalAnswer.points,
			tolerance,
		)

		const fullyCorrect =
			graded.filter((p) => p.correct && p.labelCorrect).length ===
			q.rules.maxPoints

		return {
			id: q.id,
			userAnswer,
			correctAnswer: q.canonicalAnswer.points,
			correct: fullyCorrect,
			type: q.type,
			mapGradedPoints: graded,
			mapReviewPoints: reviewPoints,
		}
	}

	// 📕 wordMatching grading
	// -------------------------
	// value schema: { "1": "του Δία", "2": "του Απόλλωνα" } key = blankKey (αριθμός κενού μέσα στο textTemplate), value = wordBank key (πχ "1A", "2B")
	const gradeWordMatching = (
		q: FullWordMatchingQuestion,
		userAnswer: FullAnswer | undefined,
	): FullGradedAnswer => {
		const userMap =
			userAnswer && typeof userAnswer === "object" && !Array.isArray(userAnswer)
				? (userAnswer as Record<string, string>)
				: {}

		const correctMap = q.correctAnswer

		const allCorrect = Object.keys(correctMap).every(
			(key) => userMap[key] === correctMap[key],
		)

		return {
			id: q.id,
			userAnswer,
			correctAnswer: correctMap,
			correct: allCorrect,
			type: q.type,
		}
	}

	// 💬 open text
	//  -----------
	// value schema: "Το εκλογικό σύστημα είναι..." Απλό string. Το grading (AI) λαμβάνει αυτό το string αυτούσιο.
	const gradeOpenTextAsync = async (
		q: FullOpenTextQuestion,
		userAnswer: FullAnswer | undefined,
	): Promise<FullGradedAnswer> => {
		const text = typeof userAnswer === "string" ? userAnswer.trim() : ""

		// ✅ αν κενό → κατευθείαν fail, χωρίς API call
		if (!text) {
			return {
				id: q.id,
				userAnswer,
				correctAnswer: q.correctAnswer,
				correct: false,
				type: q.type,
				openTextScores: {
					content: 0,
					coverage: 0,
					language: 0,
					wordLimit: 0,
					total: 0,
				},
			}
		}

		// υπολογισμός λέξεων
		const wordCount = text ? text.split(/\s+/).filter(Boolean).length : 0

		// αν ξεπερνά τις 200 λέξεις → fail χωρίς API call
		if (wordCount > 200) {
			return {
				id: q.id,
				userAnswer,
				correctAnswer: q.correctAnswer,
				correct: false,
				type: q.type,
				openTextScores: {
					content: 0,
					coverage: 0,
					language: 0,
					wordLimit: 0,
					total: 0,
				},
			}
		}

		// console.log(" test if url not used here load. url:", url);
		// console.log("url in: url /api/grade/open-text-simple", urlOpenText);
		try {
			const response = await axios.post(
				`${urlOpenText}/api/grade/open-text-simple`,
				{
					question: q.question,
					correctAnswer: q.correctAnswer,
					studentText: text,
					maxWords: q.maxWords,
				},
			)

			const data = response.data

			return {
				id: q.id,
				userAnswer,
				correctAnswer: q.correctAnswer,
				correct: data.pass,
				type: q.type,
				openTextScores: data.scores,
			}
		} catch (error) {
			console.error("OpenText grading failed:", error)

			return {
				id: q.id,
				userAnswer,
				correctAnswer: q.correctAnswer,
				correct: false,
				type: q.type,
				openTextScores: {
					content: 0,
					coverage: 0,
					language: 0,
					wordLimit: 0,
					total: 0,
				},
			}
		}
	}

	// MAIN gradeAll
	const gradeAll = async (
		questions: FullQuestion[],
		answers: Record<string, FullAnswer>,
	): Promise<GradeAllResult> => {
		let correct = 0
		const results: FullGradedAnswer[] = []

		for (const q of questions) {
			const userAnswer = answers[q.id]

			let result: FullGradedAnswer | null = null

			switch (q.type) {
				case "multipleChoice":
					result = gradeMultipleChoice(q, userAnswer)
					break

				case "shortText":
					result = gradeShortText(q, userAnswer)
					break

				case "matching":
					result = gradeMatching(q, userAnswer)
					break

				case "multiSelect":
					result = gradeMultiSelect(q, userAnswer)
					break

				case "listInput":
					result = gradeListInput(q, userAnswer)
					break

				case "trueFalseGroup":
					result = gradeTrueFalseGroup(q, userAnswer)
					break

				case "categorization":
					result = gradeCategorization(q, userAnswer)
					break

				case "mapPoints":
					result = gradeMapPoints(q, userAnswer)
					break

				case "wordMatching":
					result = gradeWordMatching(q, userAnswer)
					break

				case "openText":
					result = await gradeOpenTextAsync(q, userAnswer)
					break

				case "trueFalseNA":
					result = gradeTrueFalseNA(q, userAnswer)
					break
			}

			if (result) {
				if (result.correct) correct++
				results.push(result)
			}
		}

		return {
			results,
			score: correct,
		}
	}

	return {
		gradeAll,
	}
}
