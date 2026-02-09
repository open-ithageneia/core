import type { GeoQuestion, MapPoint } from "../types/geoTypes"

//HELPER
// διαλέγει τυχαία ΜΟΝΟ ερώτηση που έχει rules.map === true
// αυτό είναι μονο για dev. αλλιώς η ερώτηση θα έρχετε αλλιώς
export const pickRandomQuestion = (questions: GeoQuestion[]) => {
	const mapQuestions = questions.filter((question) => question.rules?.map)
	if (mapQuestions.length === 0) return null

	const index = Math.floor(Math.random() * mapQuestions.length)
	return mapQuestions[index]
}

// Σημεία απο την απάντηση
// μετατρέπει το canonicalAnswer της ερώτησης σε MapPoint[]
export const getCanonicalPoints = (
	question: GeoQuestion | null,
): MapPoint[] => {
	if (!question) return []

	const canonical = question.canonicalAnswer
	if (!canonical || canonical.type !== "points") return []

	return canonical.points.map((point) => ({
		x: point.x,
		y: point.y,
		label: point.label,
	}))
}
