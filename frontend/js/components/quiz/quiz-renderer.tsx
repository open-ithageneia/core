import type { ReactNode } from "react"
import DragAndDrop from "@/components/quiz/drag-and-drop"
import FillInTheBlank from "@/components/quiz/fill-in-the-blank"
import Listening from "@/components/quiz/listening"
import MapPointer from "@/components/quiz/map-pointer"
import Matching from "@/components/quiz/matching"
import MultipleChoice from "@/components/quiz/multiple-choice"
import OpenEnded from "@/components/quiz/open-ended"
import { QuizResultsProvider } from "@/components/quiz/shared/quiz-results-context"
import TrueFalse from "@/components/quiz/true-false"
import type { QuizData } from "@/types/models"

export function QuizRenderer({
	item,
	index,
	forceValidation,
	onScore,
	badge,
}: {
	item: QuizData[number]
	index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
	badge?: ReactNode
}) {
	const content = (() => {
		switch (item.quiz_type) {
			case "Statement": {
				if (item.type === "TRUE_FALSE") {
					return (
						<TrueFalse
							item={item}
							item_index={index}
							forceValidation={forceValidation}
							onScore={onScore}
						/>
					)
				}
				return (
					<MultipleChoice
						item={item}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			case "DragAndDrop": {
				return (
					<DragAndDrop
						item={item}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			case "OpenEnded": {
				return (
					<OpenEnded
						item={item}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			case "FillInTheBlank": {
				return (
					<FillInTheBlank
						item={item}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			case "Matching": {
				return (
					<Matching
						item={item}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			case "MapPointer": {
				return (
					<MapPointer
						item={item}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			case "Listening": {
				return (
					<Listening
						item={item}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			default:
				return (
					<div className="rounded-lg border p-4 text-sm text-gray-500">
						Μη υποστηριζόμενος τύπος ερώτησης:{" "}
						{(item as { quiz_type: string }).quiz_type}
					</div>
				)
		}
	})()

	return <QuizResultsProvider badge={badge}>{content}</QuizResultsProvider>
}
