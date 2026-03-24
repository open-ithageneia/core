import { useState } from "react"
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

const TrueFalseStatementQuestion = ({
	question,
	userAnswer,
	onChange,
	gradedAnswer,
	showGrading,
}: Props) => {
	const content = question.content as TrueFalseContent

	const [localAnswers, setLocalAnswers] = useState<Record<number, boolean>>(
		userAnswer?.type === "multi_tf" ? userAnswer.values : {},
	)

	const handleSelect = (index: number, value: boolean) => {
		const updated = {
			...localAnswers,
			[index]: value,
		}

		setLocalAnswers(updated)

		onChange({
			type: "multi_tf",
			values: updated,
		})
	}

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

				{/* image */}
				{content.prompt_asset_id && (
					<QuestionMediaBlock
						text={content.prompt_text}
						assetId={content.prompt_asset_id}
					/>
				)}

				{/* statements */}
				{content.choices.map((choice, index) => (
					<div
						key={`${question.id}-${choice.text}`}
						className="flex gap-4 items-center"
					>
						<span className="flex-1">{choice.text}</span>

						<label>
							<input
								type="radio"
								name={`q-${question.id}-${index}`}
								checked={
									userAnswer?.type === "multi_tf" &&
									userAnswer.values[index] === true
								}
								onChange={() => handleSelect(index, true)}
							/>
							Σωστό
						</label>

						<label>
							<input
								type="radio"
								name={`q-${question.id}-${index}`}
								checked={
									userAnswer?.type === "multi_tf" &&
									userAnswer.values[index] === false
								}
								onChange={() => handleSelect(index, false)}
							/>
							Λάθος
						</label>
					</div>
				))}

				{/* {correctAnswerBlock} */}
			</div>
		</div>
	)
}

export default TrueFalseStatementQuestion
