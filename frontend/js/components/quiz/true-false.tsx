import { useEffect } from "react"
import QuizCard from "@/components/quiz/shared/quiz-card"
import ValidationButton from "@/components/quiz/shared/validation-button"
import { useTrueFalse } from "@/hooks/quiz/use-true-false"
import { cn } from "@/lib/utils"
import { QUIZ_INSTRUCTIONS } from "@/types/enums"
import type { StatementModel } from "@/types/models"

type TrueFalseProps = {
	item: StatementModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

export default function TrueFalse({
	item,
	item_index,
	forceValidation,
	onScore,
}: TrueFalseProps) {
	const {
		choices,
		answers,
		showValidation,
		setShowValidation,
		showValidationButton,
		allAnswered,
		selectAnswer,
		results,
		correctAnswersCount,
	} = useTrueFalse(item, { forceValidation })

	useEffect(() => {
		if (showValidation && onScore) {
			onScore(correctAnswersCount, choices.length)
		}
	}, [showValidation, onScore, correctAnswersCount, choices.length])

	return (
		<QuizCard
			title={`Ερώτηση ${item_index}`}
			category={item.category}
			instruction={QUIZ_INSTRUCTIONS.TRUE_FALSE}
			promptText={item.content.prompt_text}
			promptAssetUrl={item.content.prompt_asset_url}
		>
			<div className="space-y-3">
				{choices.map((choice, index) => (
					<div
						key={index}
						className={cn(
							"flex items-center justify-between gap-4 rounded-lg border p-3 transition-colors",
							showValidation &&
								results[index] === true &&
								"border-green-500 bg-green-50 dark:bg-green-950",
							showValidation &&
								results[index] === false &&
								"border-red-500 bg-red-50 dark:bg-red-950",
						)}
					>
						<span className="text-sm">
							{choice.text}
							{choice.asset_url && (
								<img
									src={choice.asset_url}
									alt={choice.text ?? `Δήλωση ${index + 1}`}
									className="mt-2 max-h-40 rounded"
								/>
							)}
						</span>

						<div className="flex shrink-0 gap-2">
							<button
								type="button"
								disabled={showValidation}
								onClick={() => selectAnswer(index, true)}
								className={cn(
									"rounded-md border px-3 py-1 text-sm font-medium transition-colors",
									answers[index] === true &&
										"border-blue-500 bg-blue-50 dark:bg-blue-950",
									answers[index] !== true &&
										!showValidation &&
										"hover:bg-muted",
								)}
							>
								Σωστό
							</button>
							<button
								type="button"
								disabled={showValidation}
								onClick={() => selectAnswer(index, false)}
								className={cn(
									"rounded-md border px-3 py-1 text-sm font-medium transition-colors",
									answers[index] === false &&
										"border-blue-500 bg-blue-50 dark:bg-blue-950",
									answers[index] !== false &&
										!showValidation &&
										"hover:bg-muted",
								)}
							>
								Λάθος
							</button>
						</div>
					</div>
				))}
			</div>

			{allAnswered && showValidationButton && (
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
