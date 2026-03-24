// core\frontend\js\trueFalse-alkis\core-transfer\pages\CoreTestFullQuestion.tsx

import MultipleChoiceQuestion from "../components/MultipleChoiceQuestion"
import TrueFalseStatementQuestion from "../components/TrueFalseStatementQuestion"
import type { CoreAnswer, CoreGradedAnswer } from "../types/client.types"
import { StatementType } from "../types/enums"
import type { Statement } from "../types/models"

type Props = {
	question: Statement
	userAnswer?: CoreAnswer
	onChange: (value: CoreAnswer) => void
	gradedAnswer?: CoreGradedAnswer
	showGrading?: boolean
}

const CoreTestFullQuestion = ({
	question,
	userAnswer,
	onChange,
	gradedAnswer,
	showGrading,
}: Props) => {
	// dispatcher ανά type
	if (question.type === StatementType.MULTIPLE_CHOICE) {
		// console.log(question)

		return (
			<MultipleChoiceQuestion
				question={question}
				userAnswer={userAnswer}
				onChange={onChange}
				gradedAnswer={gradedAnswer}
				showGrading={showGrading}
			/>
		)
	}

	if (question.type === StatementType.TRUE_FALSE) {
		// console.log(question)
		return (
			<TrueFalseStatementQuestion
				question={question}
				userAnswer={userAnswer}
				onChange={onChange}
				gradedAnswer={gradedAnswer}
				showGrading={showGrading}
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
