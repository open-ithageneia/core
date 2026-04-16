import QuizCard from "@/components/quiz/shared/QuizCard"
import ValidationButton from "@/components/quiz/shared/ValidationButton"
import { useMultipleChoice } from "@/hooks/useMultipleChoice"
import { cn } from "@/lib/utils"
import { ValidationStatus } from "@/types/enums"
import type { StatementModel } from "@/types/models"

type MultipleChoiceProps = {
	item: StatementModel
	item_index: number
}

export default function MultipleChoice({ item, item_index }: MultipleChoiceProps) {
	const {
		selectedIndex,
		showValidation,
		setShowValidation,
		hasSelection,
		selectChoice,
		choiceStates,
		correctAnswersCount,
		choices,
	} = useMultipleChoice(item)

	return (
		<QuizCard
			title={`Ερώτηση ${item_index}`}
			promptText={item.content.prompt_text}
			promptAssetUrl={item.content.prompt_asset_url}
		>
			<div className="space-y-3">
				{choices.map((choice, index) => (
					<button
						// biome-ignore lint/suspicious/noArrayIndexKey: stable list of choices
						key={index}
						type="button"
						disabled={showValidation}
						onClick={() => selectChoice(index)}
						className={cn(
							"w-full rounded-lg border p-3 text-left text-sm transition-colors",
							!showValidation &&
								selectedIndex === index &&
								"border-blue-500 bg-blue-50 dark:bg-blue-950",
							!showValidation &&
								selectedIndex !== index &&
								"hover:bg-muted",
							showValidation &&
								choiceStates[index] === ValidationStatus.Correct &&
								"border-green-500 bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-300",
							showValidation &&
								choiceStates[index] === ValidationStatus.Incorrect &&
								"border-red-500 bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300",
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

				{hasSelection && (
					<ValidationButton
						showValidation={showValidation}
						onValidate={() => setShowValidation(true)}
						correctAnswersCount={correctAnswersCount}
						totalScore={1}
					/>
				)}
			</div>
		</QuizCard>
	)
}
