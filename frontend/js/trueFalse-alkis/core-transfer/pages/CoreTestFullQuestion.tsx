// frontend/src/core-transfer/pages/CoreTestFullQuestion.tsx

import TrueFalseQuestion from "../components/TrueFalseQuestion"
import { StatementType } from "../types/enums"
import type { Statement } from "../types/models"

type Props = {
	question: Statement
	userAnswer?: number
	onChange: (value: number, order: number[]) => void
}

const CoreTestFullQuestion = ({ question, userAnswer, onChange }: Props) => {
	// dispatcher ανά type
	if (question.type === StatementType.TRUE_FALSE) {
		return (
			<TrueFalseQuestion
				question={question}
				userAnswer={userAnswer}
				onChange={onChange}
			/>
		)
	}

	// fallback message
	return (
		<div className="text-red-500 text-sm">
			Unsupported question type: {question.type}
		</div>
	)
}

export default CoreTestFullQuestion
