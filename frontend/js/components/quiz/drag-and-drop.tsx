import { useEffect } from "react"
import DraggableChip from "@/components/quiz/shared/draggable-chip"
import DroppableCell from "@/components/quiz/shared/droppable-cell"
import QuizCard from "@/components/quiz/shared/quiz-card"
import QuizDndProvider from "@/components/quiz/shared/quiz-dnd-provider"
import ValidationButton from "@/components/quiz/shared/validation-button"
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table"
import { useDragAndDrop } from "@/hooks/quiz/use-drag-and-drop"
import { QUIZ_INSTRUCTIONS, ValidationStatus } from "@/types/enums"
import type { DragAndDropModel } from "@/types/models"

type DragNDropProps = {
	item: DragAndDropModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

export default function DragAndDrop({
	item,
	item_index,
	forceValidation,
	onScore,
}: DragNDropProps) {
	const {
		availableValues,
		showValidation,
		setShowValidation,
		showValidationButton,
		maxRows,
		tableValues,
		totalScore,
		isTableComplete,
		correctAnswersCount,
		clearCell,
		getCellValidationState,
		getCorrectValue,
		handleDragEnd,
	} = useDragAndDrop(item, { forceValidation })

	useEffect(() => {
		if (showValidation && onScore) {
			onScore(correctAnswersCount, totalScore)
		}
	}, [showValidation, onScore, correctAnswersCount, totalScore])

	const choicesBank = (
		<div className="rounded-xl border bg-muted/30 p-2">
			<div className="flex flex-wrap gap-1">
				{availableValues.map((value) => (
					<DraggableChip
						key={value}
						id={`chip-${value}`}
						value={value}
						disabled={showValidation}
					/>
				))}
			</div>
		</div>
	)

	return (
		<QuizDndProvider
			onDragEnd={(sourceValue, targetId) =>
				handleDragEnd(sourceValue, targetId)
			}
		>
			<QuizCard
				title={`Ερώτηση ${item_index}`}
				category={item.category}
				instruction={QUIZ_INSTRUCTIONS.DRAG_AND_DROP}
				headerExtra={!showValidation ? choicesBank : null}
			>
				<div className="overflow-x-auto rounded-xl border">
					<Table className="table-fixed w-full">
						<TableHeader>
							<TableRow>
								{item.content.map((group, index) => (
									<TableHead
										key={group.title}
										className={`w-28 sm:w-48 border-b text-center text-xs sm:text-sm font-semibold p-1 sm:p-2 ${
											index !== 0 ? "border-l" : ""
										}`}
									>
										{group.title}
									</TableHead>
								))}
							</TableRow>
						</TableHeader>

						<TableBody>
							{Array.from({ length: maxRows }).map((_, rowIndex) => (
								<TableRow
									key={`row-${rowIndex}`}
									className={rowIndex % 2 === 0 ? "bg-muted/20" : ""}
								>
									{item.content.map((group, colIndex) => {
										const cellValue = tableValues[rowIndex][colIndex]
										const validationState = getCellValidationState(
											rowIndex,
											colIndex,
										)
										const correctValue = getCorrectValue(rowIndex, colIndex)

										return (
											<TableCell
												key={`${group.title}-${rowIndex}`}
												className={colIndex !== 0 ? "border-l" : ""}
											>
												<div className="flex flex-col gap-1">
													<DroppableCell
														id={`cell-${rowIndex}-${colIndex}`}
														value={cellValue}
														disabled={Boolean(cellValue)}
														validationState={validationState}
														isLocked={showValidation}
														onRemove={() => clearCell(rowIndex, colIndex)}
													/>
													{validationState === ValidationStatus.Incorrect &&
														correctValue && (
															<DroppableCell
																id={`correctCell-${rowIndex}-${colIndex}`}
																value={correctValue}
																disabled={true}
																validationState={ValidationStatus.Correct}
																isLocked={true}
																onRemove={() => {}}
															/>
														)}
												</div>
											</TableCell>
										)
									})}
								</TableRow>
							))}
						</TableBody>
					</Table>
				</div>

				{isTableComplete && showValidationButton && (
					<ValidationButton
						showValidation={showValidation}
						onValidate={() => setShowValidation(true)}
					/>
				)}
			</QuizCard>
		</QuizDndProvider>
	)
}
