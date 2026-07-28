import { useEffect } from "react"
import QuizCard from "@/components/quiz/shared/quiz-card"
import StatementPrompt from "@/components/quiz/shared/statement-prompt"
import ValidationButton from "@/components/quiz/shared/validation-button"
import { useTrueFalse } from "@/hooks/quiz/use-true-false"
import { cn } from "@/lib/utils"
import { QUIZ_INSTRUCTIONS } from "@/types/enums"
import type { StatementModel } from "@/types/models"

const ANSWER_OPTIONS: { label: string; value: boolean }[] = [
	{ label: "Σωστό", value: true },
	{ label: "Λάθος", value: false },
]

type TrueFalseProps = {
	item: StatementModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
	/** Render only the prompt + choices, without the card or validation button.
	 * Used when embedded as part of a linked (combined) statement card. */
	bare?: boolean
}

export default function TrueFalse({
	item,
	item_index,
	forceValidation,
	onScore,
	bare,
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

	const body = (
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

					<div className="flex shrink-0 gap-1">
						{ANSWER_OPTIONS.map(({ label, value }) => {
							const isSelected = answers[index] === value
							const isCorrectAnswer = choice.is_correct === value
							return (
								<button
									key={label}
									type="button"
									disabled={showValidation}
									onClick={() => selectAnswer(index, value)}
									className={cn(
										"rounded-md border px-3 py-1 text-sm font-medium transition-colors",
										!showValidation &&
											isSelected &&
											"border-blue-500 bg-blue-50 dark:bg-blue-950",
										!showValidation && !isSelected && "hover:bg-muted",
										// After validation the correct answer is always marked, so a
										// wrong pick shows both what was chosen and what it should
										// have been.
										showValidation &&
											isCorrectAnswer &&
											"border-green-500 bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-300",
										showValidation &&
											isSelected &&
											!isCorrectAnswer &&
											"border-red-500 bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300",
										showValidation &&
											isSelected &&
											"ring-2 ring-blue-500 ring-offset-1",
									)}
								>
									{label}
								</button>
							)
						})}
					</div>
				</div>
			))}
		</div>
	)

	if (bare) {
		return (
			<div className="space-y-3">
				<StatementPrompt
					instruction={QUIZ_INSTRUCTIONS.TRUE_FALSE}
					promptText={item.content.prompt_text}
					promptAssetUrl={item.content.prompt_asset_url}
					promptAudioUrl={item.content.prompt_audio_url}
				/>
				{body}
			</div>
		)
	}

	return (
		<QuizCard
			title={`Ερώτηση ${item_index}`}
			category={item.category}
			instruction={QUIZ_INSTRUCTIONS.TRUE_FALSE}
			promptText={item.content.prompt_text}
			promptAssetUrl={item.content.prompt_asset_url}
			promptAudioUrl={item.content.prompt_audio_url}
		>
			{body}

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
