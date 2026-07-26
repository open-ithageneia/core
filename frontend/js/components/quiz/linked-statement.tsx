import { useCallback, useEffect, useState } from "react"
import MultipleChoice from "@/components/quiz/multiple-choice"
import QuizCard from "@/components/quiz/shared/quiz-card"
import ValidationButton from "@/components/quiz/shared/validation-button"
import TrueFalse from "@/components/quiz/true-false"
import { useValidation } from "@/hooks/quiz/use-validation"
import { StatementType } from "@/types/enums"
import type { StatementModel } from "@/types/models"

type Score = { correct: number; total: number }
const ZERO_SCORE: Score = { correct: 0, total: 0 }

type LinkedStatementProps = {
	item: StatementModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

function StatementPart({
	item,
	forceValidation,
	onScore,
}: {
	item: StatementModel
	forceValidation: boolean
	onScore: (correct: number, total: number) => void
}) {
	const Component =
		item.type === StatementType.TRUE_FALSE ? TrueFalse : MultipleChoice
	return (
		<Component
			bare
			item={item}
			item_index={0}
			forceValidation={forceValidation}
			onScore={onScore}
		/>
	)
}

/**
 * Renders a statement together with its linked `second_part` as a single
 * combined card: both parts share one "validate" button and their scores are
 * summed into a single result for the question.
 */
export default function LinkedStatement({
	item,
	item_index,
	forceValidation,
	onScore,
}: LinkedStatementProps) {
	const secondPart = item.second_part
	const { showValidation, setShowValidation, showValidationButton } =
		useValidation({ forceValidation })

	const [firstScore, setFirstScore] = useState<Score>(ZERO_SCORE)
	const [secondScore, setSecondScore] = useState<Score>(ZERO_SCORE)

	const reportFirst = useCallback(
		(correct: number, total: number) => setFirstScore({ correct, total }),
		[],
	)
	const reportSecond = useCallback(
		(correct: number, total: number) => setSecondScore({ correct, total }),
		[],
	)

	useEffect(() => {
		if (showValidation && onScore) {
			onScore(
				firstScore.correct + secondScore.correct,
				firstScore.total + secondScore.total,
			)
		}
	}, [showValidation, onScore, firstScore, secondScore])

	return (
		<QuizCard title={`Ερώτηση ${item_index}`} category={item.category}>
			<StatementPart
				item={item}
				forceValidation={showValidation}
				onScore={reportFirst}
			/>

			{secondPart && (
				<>
					<hr className="border-border" />
					<StatementPart
						item={secondPart}
						forceValidation={showValidation}
						onScore={reportSecond}
					/>
				</>
			)}

			{showValidationButton && (
				<div className="mt-3">
					<ValidationButton
						showValidation={showValidation}
						onValidate={() => setShowValidation(true)}
					/>
				</div>
			)}
		</QuizCard>
	)
}
