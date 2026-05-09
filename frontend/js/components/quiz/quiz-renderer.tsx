import type { ReactNode } from "react"
import DragAndDrop from "@/components/quiz/drag-and-drop"
import FillInTheBlank from "@/components/quiz/fill-in-the-blank"
import Matching from "@/components/quiz/matching"
import MultipleChoice from "@/components/quiz/multiple-choice"
import OpenEnded from "@/components/quiz/open-ended"
import { QuizResultsProvider } from "@/components/quiz/shared/quiz-results-context"
import TrueFalse from "@/components/quiz/true-false"
import type {
	DragAndDropContent,
	DragAndDropModel,
	FillInTheBlankContent,
	FillInTheBlankModel,
	MatchingContent,
	MatchingModel,
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
}: {
	item: TrainingData[number]
	index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
	badge?: ReactNode
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
						item_index={index}
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
			case "Matching": {
				const matchingItem = {
					id: item.id,
					category: item.category,
					content: item.content as MatchingContent,
				} as MatchingModel
				return (
					<Matching
						item={matchingItem}
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

	return <QuizResultsProvider badge={badge}>{content}</QuizResultsProvider>
}
