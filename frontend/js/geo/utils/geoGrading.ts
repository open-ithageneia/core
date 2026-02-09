import type { GradedPoint, LabelCheckResult, MapPoint } from "../types/geoTypes"
import { simplifyLang } from "./simplifyLang"

// GRADING (ΜΟΝΟ ΣΗΜΕΙΟ)
// απόσταση δύο σημείων σε ποσοστά → μου επιστρέφει την υποτείνουσα  (≈ το διάνυσμα της απόστασης)
export const distancePct = (
	a: { x: number; y: number },
	b: { x: number; y: number },
) => {
	const dx = a.x - b.x
	const dy = a.y - b.y
	return Math.sqrt(dx * dx + dy * dy)
}

export const isLabelCorrect = (
	userLabel: string,
	canonicalLabel: string,
): LabelCheckResult => {
	const cleanUser = userLabel.trim()
	const cleanCanonical = canonicalLabel.trim()

	// exact match → όλα σωστά
	if (cleanUser === cleanCanonical) {
		return { correct: true, hasSpellingErrors: false }
	}

	// simplified match → σωστό αλλά με ορθογραφικά
	const simplifiedUser = simplifyLang(cleanUser)
	const simplifiedCanonical = simplifyLang(cleanCanonical)

	if (simplifiedUser === simplifiedCanonical) {
		return { correct: true, hasSpellingErrors: true }
	}

	// αποτυχία
	return { correct: false, hasSpellingErrors: false }
}

// ελέγχει αν τα user points πέφτουν κοντά σε canonical
export const gradePoints = (
	userPoints: MapPoint[],
	canonicalPoints: { x: number; y: number; label: string }[],
	tolerancePct: number,
): GradedPoint[] => {
	const remaining = [...canonicalPoints] // για να μην αγγίζουμε το array των απαντήσεων

	// με το map ελέγχουμε όλα τα σημειά που έχει υποβάλει ο μαθητής
	return userPoints.map((userPoint) => {
		// δηλ ξεκινάμε απο το "δεν έχει βρεθεί τιποτα" και τα λεκτικά είναι λάθος
		let matchedIndex = -1
		let labelResult = {
			correct: false,
			hasSpellingErrors: false,
		}

		// ελέγχει αν έστω και ένα σημείο, απο τα σημεία της απάντησης είναι εντώς του tolerance (αρα αν έχει απαντηθει σωστα) - TODO να το σκευτώ λίγο γιατί πολλά σημεία ήταν πολύ κοντά το ένα στο άλλο στις απαντήσεις
		const isCorrect = remaining.some((canonicalPoint, i) => {
			// βρίσκει την αποσταση μεταξύ σημείου μαθητή και απάντησης
			const dist = distancePct(userPoint, canonicalPoint)
			if (dist <= tolerancePct) {
				matchedIndex = i
				return true
			}
			return false
		})

		if (matchedIndex !== -1) {
			const matchedCanonical = remaining[matchedIndex]
			labelResult = isLabelCorrect(userPoint.label, matchedCanonical.label)
			remaining.splice(matchedIndex, 1)
		}

		return {
			...userPoint,
			correct: isCorrect,
			labelCorrect: labelResult.correct,
			hasSpellingErrors: labelResult.hasSpellingErrors,
		}
	})
}

// φτιάχνει τα σημεία που θα εμφανιστούν μετά το submit
export const buildReviewPoints = (
	graded: GradedPoint[],
	canonicalPoints: MapPoint[],
	tolerancePct: number,
): MapPoint[] => {
	const remainingCanonical = [...canonicalPoints]

	graded.forEach((gradedPoint) => {
		if (!gradedPoint.correct) return

		// θα πρέπει να δούμε ποια απο τα σημεία που έχουν χαρακτηριστεί ως σωστά ταυτίζονται με αυτα της απάντησης. δεν βρίκα κάποιο καλήτερο τρόπο και υπολογίζω για δεύτερη φορά το διανυσμα της μεταξύ τους απόστασης
		const index = remainingCanonical.findIndex((canonicalPoint) => {
			const dx = gradedPoint.x - canonicalPoint.x
			const dy = gradedPoint.y - canonicalPoint.y
			const distance = Math.sqrt(dx * dx + dy * dy)
			return distance <= tolerancePct
		})

		if (index !== -1) {
			remainingCanonical.splice(index, 1)
		}
	})

	return [
		...graded.map((g) => ({
			x: g.x,
			y: g.y,
			label: g.label,
		})),
		...remainingCanonical,
	]
}
