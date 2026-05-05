import type { ReactNode } from "react"
import DragAndDrop from "@/components/quiz/DragAndDrop"
import FillInTheBlank from "@/components/quiz/FillInTheBlank"
import MultipleChoice from "@/components/quiz/MultipleChoice"
import OpenEnded from "@/components/quiz/OpenEnded"
import { QuizResultsProvider } from "@/components/quiz/shared/QuizResultsContext"
import TrueFalse from "@/components/quiz/TrueFalse"
import type {
	DragAndDropContent,
	DragAndDropModel,
	FillInTheBlankContent,
	FillInTheBlankModel,
	OpenEndedContent,
	OpenEndedModel,
	StatementModel,
	TrainingData,
} from "@/types/models"

export function QuizRenderer({
	item,
	index,
	forceValidation,
	onScore,
	badge,
	hideScore,
}: {
	item: TrainingData[number]
	index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
	badge?: ReactNode
	hideScore?: boolean
}) {
	const content = (() => {
		switch (item.quiz_type) {
			case "Statement": {
				const statementItem = {
					id: item.id,
					category: item.category,
					content: item.content,
					type:
						"choices" in item.content &&
						Array.isArray(item.content.choices) &&
						item.content.choices.length === 2
							? "TRUE_FALSE"
							: "MULTIPLE_CHOICE",
				} as StatementModel
				if (statementItem.type === "TRUE_FALSE") {
					return (
						<TrueFalse
							item={statementItem}
							item_index={index}
							forceValidation={forceValidation}
							onScore={onScore}
						/>
					)
				}
				return (
					<MultipleChoice
						item={statementItem}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			case "DragAndDrop": {
				const dndItem = {
					id: item.id,
					category: item.category,
					content: item.content as DragAndDropContent,
				} as DragAndDropModel
				return (
					<DragAndDrop
						item={dndItem}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			case "OpenEnded": {
				const openEndedItem = {
					id: item.id,
					category: item.category,
					content: item.content as OpenEndedContent,
				} as OpenEndedModel
				return (
					<OpenEnded
						item={openEndedItem}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			case "FillInTheBlank": {
				const fitbItem = {
					id: item.id,
					category: item.category,
					content: item.content as FillInTheBlankContent,
				} as FillInTheBlankModel
				return (
					<FillInTheBlank
						item={fitbItem}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			default:
				return (
					<div className="rounded-lg border p-4 text-sm text-gray-500">
						Μη υποστηριζόμενος τύπος ερώτησης: {item.quiz_type}
					</div>
				)
		}
	})()

	return (
		<QuizResultsProvider badge={badge} hideScore={hideScore}>
			{content}
		</QuizResultsProvider>
	)
}
