import { cn } from "@/lib/utils"
import { ValidationStatus } from "@/types/enums"
import type { QuizChoice } from "@/types/models"
import type { ValidationState } from "@/types/quiz"

type ChoiceListProps = {
	choices: QuizChoice[]
	selectedIndices: Set<number>
	choiceStates: ValidationState[]
	showValidation: boolean
	onSelect: (index: number) => void
}

/** The selectable options of a multiple-choice style question. */
export default function ChoiceList({
	choices,
	selectedIndices,
	choiceStates,
	showValidation,
	onSelect,
}: ChoiceListProps) {
	return (
		<div className="space-y-3">
			{choices.map((choice, index) => (
				<button
					key={index}
					type="button"
					disabled={showValidation}
					onClick={() => onSelect(index)}
					className={cn(
						"w-full rounded-lg border p-3 text-left text-sm transition-colors",
						!showValidation &&
							selectedIndices.has(index) &&
							"border-blue-500 bg-blue-50 dark:bg-blue-950",
						!showValidation && !selectedIndices.has(index) && "hover:bg-muted",
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
		</div>
	)
}
