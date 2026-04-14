import { DragDropProvider } from "@dnd-kit/react"
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
import type { DragAndDropModel } from "@/types/models"

type DragNDropProps = {
	item: DragAndDropModel
}

export default function DragAndDrop({ item }: DragNDropProps) {
	const {
		availableValues,
		showValidation,
		setShowValidation,
		maxRows,
		tableValues,
		totalScore,
		isTableComplete,
		correctAnswersCount,
		clearCell,
		getCellValidationState,
		handleDragEnd,
	} = useDragAndDrop(item)

	return (
		<QuizCard title="Drag and Drop">
			<DragDropProvider
				onDragEnd={({ operation }) => {
					if (!operation.source || !operation.target) return
					handleDragEnd(
						operation.source.data.value,
						String(operation.target.id),
					)
				}}
			>
				<div className="rounded-xl border bg-muted/30 p-4">
					<div className="flex flex-wrap gap-2">
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
										className={`w-48 border-b text-center font-semibold ${
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
									// biome-ignore lint/suspicious/noArrayIndexKey: static grid, order never changes
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
												// biome-ignore lint/suspicious/noArrayIndexKey: static grid, order never changes
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

				{isTableComplete && (
					<ValidationButton
						showValidation={showValidation}
						onValidate={() => setShowValidation(true)}
						correctAnswersCount={correctAnswersCount}
						totalScore={totalScore}
					/>
				)}
			</DragDropProvider>
		</QuizCard>
	)
}
