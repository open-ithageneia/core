// core\frontend\js\trueFalse-alkis\core-transfer\components\MultipleChoiceQuestion.tsx

import { useMemo } from "react"
import type { CoreAnswer, CoreGradedAnswer } from "../types/client.types"
import type { Statement, TrueFalseContent } from "../types/models"
// import { formatCorrectAnswer } from "../utils/formatGradedAnswer"
import QuestionMediaBlock from "./QuestionMediaBlock"

type Props = {
	question: Statement
	userAnswer?: CoreAnswer
	onChange: (value: CoreAnswer) => void
	gradedAnswer?: CoreGradedAnswer
	showGrading?: boolean
}

const MultipleChoiceQuestion = ({
	question,
	userAnswer,
	onChange,
	gradedAnswer,
	showGrading,
}: Props) => {
	// κάνουμε type narrowing
	const content = question.content as TrueFalseContent

	// αυτό προστέθηκε για την λειτουργία shuffled. To προβλημα που προσπαθούμε να λύσουμε είναι το εξής: σε κάθε render αλλάζει η σειρά που εμφανίζονται οι απαντήσεις. Εμείς έχουμε κρατήσει που βρίσκονται οι αρχικές θέσεις των ερωτήσεων και που πήγαν μετά και έτσι μπορούμε να αντιστοιχισουμε την απάντηση του user στην σειρά που του εμφανίστηκε με την αρχική θέση της απάντησης αυτής στα data
	// ο λόγος που χρησιμοποιούμε useMemo είναι γιατί δεν θέλουμε να κάνει rerender και άρα reshuffle τις απαντήσεις πριν να είναι ώρα.
	// biome-ignore lint/correctness/useExhaustiveDependencies: shuffle only once per mount
	const shuffledChoices = useMemo(() => {
		// φτιάχνουμε array με indexes των επιλογών
		// πχ choices: [A, B, C] → indexed: [0, 1, 2]
		const indexed = content.choices.map((_, i) => i)

		// κάνουμε shuffle τα indexes (όχι τα ίδια τα choices)
		// πχ [0,1,2] → [1,2,0]
		// αυτό είναι το "order": UI θέση → original index
		return indexed.sort(() => 0.5 - Math.random())
	}, []) // (αγνόησα το lint) θέλουμε shuffle μόνο στο mount (όχι σε κάθε render / change)

	// απλως τα styling classnames που μου κάνουν το κουτί πρασινο/κόκκινο μετά την αξιολογηση
	const gradedClass =
		showGrading && gradedAnswer
			? gradedAnswer.correct
				? "bg-green-50 border border-green-400"
				: "bg-red-50 border border-red-400"
			: ""

	// ενα μικρό component για την εμφάνιση του αποτελέσματος της κάθε ερώτησης
	// const correctAnswerBlock =
	//   showGrading &&
	//   gradedAnswer &&
	//   !gradedAnswer.correct ? (
	//     <div className="mt-3 p-3 bg-muted rounded text-sm">
	//       <p className="font-semibold">Σωστή απάντηση:</p>
	//       <p>{formatCorrectAnswer(gradedAnswer.correctAnswer)}</p>
	//     </div>
	//   ) : null

	return (
		<div className={`border p-4 rounded space-y-3 ${gradedClass}`}>
			<div className="border p-4 rounded space-y-3">
				{/* prompt */}
				{content.prompt_text && <p>{content.prompt_text}</p>}

				{/* image (αν υπάρχει) */}
				{content.prompt_asset_id && (
					<QuestionMediaBlock
						text={content.prompt_text}
						assetId={content.prompt_asset_id}
					/>
				)}

				{/* επιλογές */}
				{shuffledChoices.map((originalIndex, i) => {
					const choice = content.choices[originalIndex]

					return (
						<div key={`q-${question.id}-choice-${i}`}>
							<input
								type="radio"
								name={`q-${question.id}`}
								checked={
									userAnswer?.type === "single" && userAnswer.index === i
								}
								onChange={() =>
									onChange({
										type: "single",
										index: i,
										order: shuffledChoices,
									})
								}
							/>
							<span>{choice.text}</span>
						</div>
					)
				})}
				{/* {correctAnswerBlock} */}
			</div>
		</div>
	)
}

export default MultipleChoiceQuestion
