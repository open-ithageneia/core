import { useState } from "react"
import { Button } from "../../components/ui/button"
import GeoGradingSummary from "../components/GeoGradingSummary"
import MapClickQuiz from "../components/MapClickQuiz"
import geoQuestionsData from "../data/geoQuestionsData.json"
import type { GeoQuestion, GradedPoint, MapPoint } from "../types/geoTypes"

import { buildReviewPoints, gradePoints } from "../utils/geoGrading"
// UTILS / HELPERS
import {
	// διαλέγει τυχαία ΜΟΝΟ ερώτηση που έχει rules.map === true
	// αυτό είναι μονο για dev. αλλιώς η ερώτηση θα έρχετε αλλιώς
	getCanonicalPoints,
	// Σημεία απο την απάντηση
	// μετατρέπει το canonicalAnswer της ερώτησης σε MapPoint[]
	pickRandomQuestion,
} from "../utils/geoQuestionUtils"

const GeographyMaps = () => {
	// τρέχουσα ερώτηση
	const [question, setQuestion] = useState<GeoQuestion | null>(null)

	// σημεία που έχει βάλει ο χρήστης (ή που δείχνουμε ως λύσεις)
	const [points, setPoints] = useState<MapPoint[]>([])

	// αποτέλεσμα αξιολόγησης των σημείων του χρήστη (σωστό / λάθος)
	const [gradedPoints, setGradedPoints] = useState<
		(GradedPoint & { correct: boolean })[] | null
	>(null)

	// στο submit θα δείχνουμε όλα τα σημεια του user + όσα δεν βρέθηκαν
	const [displayPoints, setDisplayPoints] = useState<MapPoint[]>([])

	// flag μόνο για flow (δεν το διαβάζουμε)
	const [, setShowAnswers] = useState(false)

	// BUTTON HANDLERS
	// νέα τυχαία ερώτηση
	const handleNextQuestion = () => {
		setQuestion(pickRandomQuestion(geoQuestionsData as GeoQuestion[]))
		setPoints([])
		setGradedPoints(null)
		setShowAnswers(false)
	}

	// δείχνει τις σωστές απαντήσεις
	const handleShowAnswers = () => {
		if (!question) return

		const canonicalPoints = getCanonicalPoints(question) // μου επιστρέφει [x,y,label]

		// αντικαθιστούμε τα user points με τα canonical
		// θα αλλάξει να δείχνει τα λάθη και τις απαντήσεις
		setPoints(canonicalPoints)
		setShowAnswers(true)
	}

	// submit απαντήσεων
	const handleSubmit = () => {
		if (!question?.canonicalAnswer) return

		const tolerance = question.rules?.tolerancePct ?? 3.5

		const graded = gradePoints(
			points,
			question.canonicalAnswer.points,
			tolerance,
		)

		setGradedPoints(graded)

		const canonicalPoints = getCanonicalPoints(question)
		const reviewPoints = buildReviewPoints(graded, canonicalPoints, tolerance)

		setDisplayPoints(reviewPoints)
		console.log("graded result:", graded)
	}

	return (
		<>
			new
			<div className="p-4 space-y-4">
				<h2 className="mb-4 text-xl font-semibold text-foreground">
					Geography Maps
				</h2>

				{question && (
					<>
						<p className="mb-2 text-base text-foreground">{question.ερώτηση}</p>

						<span className="mb-2 block text-sm text-muted-foreground">
							id: {question.id}
						</span>
					</>
				)}

				<div className="mb-4">
					<MapClickQuiz
						maxWidth={900}
						points={gradedPoints ? displayPoints : points} // πριν submit → points, μετά submit → displayPoints
						setPoints={setPoints}
						maxPoints={question?.rules?.maxPoints ?? 4}
					/>
				</div>

				<div className="flex gap-3">
					<Button
						onClick={handleNextQuestion}
						className="bg-primary text-primary-foreground hover:bg-primary/90"
					>
						Νέα τυχαία ερώτηση
					</Button>

					<Button
						onClick={handleShowAnswers}
						disabled={!question}
						className="border border-border bg-background text-foreground hover:bg-accent hover:text-accent-foreground"
					>
						Δείξε απαντήσεις
					</Button>

					<Button
						onClick={handleSubmit}
						disabled={points.length === 0}
						className="bg-secondary text-secondary-foreground hover:bg-secondary/80 disabled:opacity-50"
					>
						Submit
					</Button>
				</div>

				{gradedPoints && (
					<GeoGradingSummary gradedPoints={gradedPoints} question={question} />
				)}
			</div>
		</>
	)
}

export default GeographyMaps
