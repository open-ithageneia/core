import { useEffect } from "react"
import ChoiceList from "@/components/quiz/shared/choice-list"
import QuizCard from "@/components/quiz/shared/quiz-card"
import ValidationButton from "@/components/quiz/shared/validation-button"
import { useMultipleChoice } from "@/hooks/quiz/use-multiple-choice"
import { QUIZ_INSTRUCTIONS, WordRelationType } from "@/types/enums"
import type { WordRelationModel } from "@/types/models"

type WordRelationProps = {
	item: WordRelationModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

export default function WordRelation({
	item,
	item_index,
	forceValidation,
	onScore,
}: WordRelationProps) {
	const {
		subAnswersCount,
		selectedIndices,
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

	const instruction =
		item.type === WordRelationType.ANTONYM
			? QUIZ_INSTRUCTIONS.WORD_RELATION_ANTONYM
			: QUIZ_INSTRUCTIONS.WORD_RELATION_SYNONYM
	const { before, underlined, after } = item.content.sentence

	return (
		<QuizCard
			title={`Ερώτηση ${item_index}`}
			category={item.category}
			instruction={instruction}
		>
			<p className="mb-3 text-base">
				{before}
				<u className="font-semibold underline-offset-4">{underlined}</u>
				{after}
			</p>

			<ChoiceList
				choices={choices}
				selectedIndices={selectedIndices}
				choiceStates={choiceStates}
				showValidation={showValidation}
				onSelect={selectChoice}
			/>

			{hasSelection && showValidationButton && (
				<ValidationButton
					showValidation={showValidation}
					onValidate={() => setShowValidation(true)}
				/>
			)}
		</QuizCard>
	)
}
