import AddAnswerButton from "@/components/quiz/shared/AddAnswerButton"
import PostValidationNotes from "@/components/quiz/shared/PostValidationNotes"
import QuizCard from "@/components/quiz/shared/QuizCard"
import RemoveAnswerButton from "@/components/quiz/shared/RemoveAnswerButton"
import ValidationButton from "@/components/quiz/shared/ValidationButton"
import { Input } from "@/components/ui/input"
import { useOpenEnded } from "@/hooks/useOpenEnded"
import { cn } from "@/lib/utils"
import { ValidationStatus } from "@/types/enums"
import type { OpenEndedModel } from "@/types/models"

type OpenEndedProps = {
	item: OpenEndedModel
	item_index: number
	forceValidation?: boolean
}

export default function OpenEnded({
	item,
	item_index,
	forceValidation,
}: OpenEndedProps) {
	const {
		answers,
		showValidation,
		setShowValidation,
		showValidationButton,
		hasAtLeastOneAnswer,
		states,
		correctAnswersCount,
		missedAnswers,
		canAddAnswer,
		addAnswerField,
		removeAnswerField,
		updateAnswer,
		minCorrectAnswers,
	} = useOpenEnded(item, { forceValidation })

	return (
		<QuizCard
			title={`???t?s? ${item_index}`}
			promptText={item.content.prompt_text}
			promptAssetUrl={item.content.prompt_asset_url}
		>
			<div className="space-y-3">
				{answers.map((answer, index) => (
					<div key={index} className="flex items-center gap-2">
						<Input
							type="text"
							placeholder={`?p??t?s? ${index + 1}`}
							value={answer}
							onChange={(e) => updateAnswer(index, e.target.value)}
							disabled={showValidation}
							className={cn(
								"flex-1",
								showValidation &&
									states[index] === ValidationStatus.Correct &&
									"border-green-500 bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-300",
								showValidation &&
									states[index] === ValidationStatus.Incorrect &&
									"border-red-500 bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-300",
							)}
						/>
						{!showValidation && (
							<RemoveAnswerButton onClick={() => removeAnswerField(index)} />
						)}
					</div>
				))}

				{canAddAnswer && <AddAnswerButton onClick={addAnswerField} />}

				{hasAtLeastOneAnswer && showValidationButton && (
					<ValidationButton
						showValidation={showValidation}
						onValidate={() => setShowValidation(true)}
						correctAnswersCount={correctAnswersCount}
						totalScore={minCorrectAnswers}
					/>
				)}

				{showValidation && (
					<PostValidationNotes
						title="S?st?? apa?t?se?? p?? ?e?p???:"
						notes={missedAnswers}
					/>
				)}
			</div>
		</QuizCard>
	)
}
