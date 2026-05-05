import { DragDropProvider } from "@dnd-kit/react"
import { useEffect } from "react"
import DraggableChip from "@/components/quiz/shared/DraggableChip"
import DroppableCell from "@/components/quiz/shared/DroppableCell"
import QuizCard from "@/components/quiz/shared/QuizCard"
import ValidationButton from "@/components/quiz/shared/ValidationButton"
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table"
import { useDragAndDrop } from "@/hooks/useDragAndDrop"
import { QUIZ_INSTRUCTIONS } from "@/types/enums"
import type { DragAndDropModel } from "@/types/models"

type DragNDropProps = {
	item: DragAndDropModel
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

export default function DragAndDrop({
	item,
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
		handleDragEnd,
	} = useDragAndDrop(item, { forceValidation })

	useEffect(() => {
		if (showValidation && onScore) {
			onScore(correctAnswersCount, totalScore)
		}
	}, [showValidation, onScore, correctAnswersCount, totalScore])

	return (
		<QuizCard
			title="Drag and Drop"
			instruction={QUIZ_INSTRUCTIONS.DRAG_AND_DROP}
		>
			<DragDropProvider
				onDragEnd={({ operation }) => {
					if (!operation.source || !operation.target) return
					handleDragEnd(
						operation.source.data.value,
						String(operation.target.id),
					)
				}}
			>
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

										return (
											<TableCell
												key={`${group.title}-${rowIndex}`}
												className={colIndex !== 0 ? "border-l" : ""}
											>
												<DroppableCell
													id={`cell-${rowIndex}-${colIndex}`}
													value={cellValue}
													disabled={Boolean(cellValue)}
													validationState={validationState}
													isLocked={showValidation}
													onRemove={() => clearCell(rowIndex, colIndex)}
												/>
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
			</DragDropProvider>
		</QuizCard>
	)
}
