import { useEffect } from "react"
import ChoiceList from "@/components/quiz/shared/choice-list"
import QuizCard from "@/components/quiz/shared/quiz-card"
import StatementPrompt from "@/components/quiz/shared/statement-prompt"
import ValidationButton from "@/components/quiz/shared/validation-button"
import { useMultipleChoice } from "@/hooks/quiz/use-multiple-choice"
import { QUIZ_INSTRUCTIONS } from "@/types/enums"
import type { StatementModel } from "@/types/models"

type MultipleChoiceProps = {
	item: StatementModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
	/** Render only the prompt + choices, without the card or validation button.
	 * Used when embedded as part of a linked (combined) statement card. */
	bare?: boolean
}

export default function MultipleChoice({
	item,
	item_index,
	forceValidation,
	onScore,
	bare,
}: MultipleChoiceProps) {
	const {
		subAnswersCount,
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
			onScore(correctAnswersCount, subAnswersCount)
		}
	}, [showValidation, onScore, correctAnswersCount, subAnswersCount])

	const instruction = isMultiSelect
		? QUIZ_INSTRUCTIONS.MULTIPLE_CHOICE_MULTI
		: QUIZ_INSTRUCTIONS.MULTIPLE_CHOICE_SINGLE

	const body = (
		<ChoiceList
			choices={choices}
			selectedIndices={selectedIndices}
			choiceStates={choiceStates}
			showValidation={showValidation}
			onSelect={selectChoice}
		/>
	)

	if (bare) {
		return (
			<div className="space-y-3">
				<StatementPrompt
					instruction={instruction}
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
			instruction={instruction}
			promptText={item.content.prompt_text}
			promptAssetUrl={item.content.prompt_asset_url}
			promptAudioUrl={item.content.prompt_audio_url}
		>
			{body}

			{hasSelection && showValidationButton && (
				<ValidationButton
					showValidation={showValidation}
					onValidate={() => setShowValidation(true)}
				/>
			)}
		</QuizCard>
	)
}
