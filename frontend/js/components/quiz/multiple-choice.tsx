import { useEffect } from "react"
import QuizCard from "@/components/quiz/shared/quiz-card"
import ValidationButton from "@/components/quiz/shared/validation-button"
import { useMultipleChoice } from "@/hooks/quiz/use-multiple-choice"
import { cn } from "@/lib/utils"
import { QUIZ_INSTRUCTIONS, ValidationStatus } from "@/types/enums"
import type { StatementModel } from "@/types/models"

type MultipleChoiceProps = {
	item: StatementModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

export default function MultipleChoice({
	item,
	item_index,
	forceValidation,
	onScore,
}: MultipleChoiceProps) {
	const {
		totalCorrect,
		selectedIndices,
		isMultiSelect,
		showValidation,
		setShowValidation,
		showValidationButton,
		hasSelection,
		selectChoice,
		choiceStates,
		correctAnswersCount,
		choices,
	} = useMultipleChoice(item, { forceValidation })

	useEffect(() => {
		if (showValidation && onScore) {
			onScore(correctAnswersCount, totalCorrect)
		}
	}, [showValidation, onScore, correctAnswersCount, totalCorrect])

	return (
		<QuizCard
			title={`Ερώτηση ${item_index}`}
			instruction={
				isMultiSelect
					? QUIZ_INSTRUCTIONS.MULTIPLE_CHOICE_MULTI
					: QUIZ_INSTRUCTIONS.MULTIPLE_CHOICE_SINGLE
			}
			promptText={item.content.prompt_text}
			promptAssetUrl={item.content.prompt_asset_url}
		>
			<div className="space-y-3">
				{choices.map((choice, index) => (
					<button
						key={index}
						type="button"
						disabled={showValidation}
						onClick={() => selectChoice(index)}
						className={cn(
							"w-full rounded-lg border p-3 text-left text-sm transition-colors",
							!showValidation &&
								selectedIndices.has(index) &&
								"border-blue-500 bg-blue-50 dark:bg-blue-950",
							!showValidation &&
								!selectedIndices.has(index) &&
								"hover:bg-muted",
							showValidation &&
								choiceStates[index] === ValidationStatus.Correct &&
								"border-green-500 bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-300",
							showValidation &&
								choiceStates[index] === ValidationStatus.Incorrect &&
								"border-red-500 bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300",
							showValidation &&
								selectedIndices.has(index) &&
								"ring-2 ring-blue-500 ring-offset-1",
						)}
					>
						{choice.text}
						{choice.asset_url && (
							<img
								src={choice.asset_url}
								alt={choice.text ?? `Επιλογή ${index + 1}`}
								className="mt-2 max-h-40 rounded"
							/>
						)}
					</button>
				))}

				{hasSelection && showValidationButton && (
					<ValidationButton
						showValidation={showValidation}
						onValidate={() => setShowValidation(true)}
					/>
				)}
			</div>
		</QuizCard>
	)
}
