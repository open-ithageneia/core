// core\frontend\js\trueFalse-alkis\core-transfer\pages\CoreTestFullPagePicker.tsx

import { useState } from "react"
// import data from "../data/testData.json"
import { useCoreFullGrading } from "../hooks/useCoreFullGrading"
import type { CoreAnswer, CoreGradedAnswer } from "../types/client.types"
import type { Statement } from "../types/models"
import CoreTestFullQuestion from "./CoreTestFullQuestion"

// μεταφορά απο '../data/trueFalseData.json' → props που μου έρχονται απο inertia back
type Props = {
	questions: Statement[]
}

const CoreTestFullPagePicker = ({ questions }: Props) => {
	// const CoreTestFullPagePicker = () => {
	// const questions = [...data.true_false, ...data.multiple_choice] as Statement[]

	// οι απαντήσεις έχουν την σειρά της απάντησης και το ποια απάντηση επέλεξε ο χρήστης (επειδή οι ερωτήσεις κάνουν shuffle δεν είναι απαραίτητο οτι ταυτίζετε με την σωστή σειρά της απάντησης)
	// οι απαντήσεις αποθηκεύουν:
	// - index: ποια επιλογή πάτησε ο χρήστης (στο UI μετά το shuffle)
	// - order: mapping από UI θέση → original index
	// πχ original: [A, B, C] → shuffled: [B, C, A] → order = [1, 2, 0]
	// άρα αν user πατήσει index = 0 → επέλεξε το original index 1 (B)
	const [answers, setAnswers] = useState<Record<number, CoreAnswer>>({})
	const [gradedAnswers, setGradedAnswers] = useState<CoreGradedAnswer[]>([])
	const [score, setScore] = useState<number | null>(null)

	//η λογική της διόρθωσης έχει μεταφερθεί σε δικό της hook με switch ανα τύπο ερώτησης
	// επιστρέφει αναλυτικά results και συνολικό score
	const { gradeAll } = useCoreFullGrading()

	// στην επιλογή ερώτηση όλα ίδια εκτός απο το [id]: value
	const handleChange = (id: number, value: CoreAnswer) => {
		setAnswers((prev) => ({
			...prev,
			[id]: value,
		}))
	}

	const handleSubmit = () => {
		try {
			// στέλνουμε τα αποτελέσματα (όπως έρχονται απο data) στο grading hook
			const { results, score } = gradeAll(questions, answers)

			setGradedAnswers(results)
			setScore(score)
		} catch (_error) {
			// console.error("Grading failed:", error)
		}
	}

	return (
		<div className="max-w-3xl mx-auto p-6 space-y-6">
			{questions.map((q, index) => {
				// οι ερωτήσεις που είναι απαντημένες έχουν διαφορετικό ui που δείχνει τα αποτελέσματα - βρίσκουμε το αποτέλεσμα grading για αυτή την ερώτηση (αν έχει γίνει submit)
				const graded = gradedAnswers.find((a) => a.id === q.id)

				return (
					<div key={`question-${q.id}`}>
						{/* αυξων αριθμός */}
						<p>{index + 1}.</p>

						{/* καλούμε το component που διαχειρίζεστε του διαφορετικους τύπους ερωτήσεων */}
						<CoreTestFullQuestion
							question={q}
							userAnswer={answers[q.id]}
							onChange={(value) => handleChange(q.id, value)}
							gradedAnswer={graded}
							showGrading={score !== null}
						/>

						{/* κάτω απο κάθε απαντημένη ερώτηση το UI εμφανίζει το αποτέλεσμα */}
						{/* TODO fetch legacy UI */}
						{graded && (
							<div className="text-sm mt-2">
								{graded.correct ? "✔ σωστό" : "✘ λάθος"}
							</div>
						)}
					</div>
				)
			})}

			{/* submit */}
			<button
				type="button"
				onClick={handleSubmit}
				className="px-4 py-2 bg-black text-white rounded"
			>
				Submit
			</button>

			{/* TODO fetch legacy UI */}
			{score !== null && (
				<div className="mt-6 font-bold">
					Σκορ: {score} / {questions.length}
				</div>
			)}
		</div>
	)
}

export default CoreTestFullPagePicker
