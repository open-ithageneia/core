import { useEffect } from "react"
import ChoicesBank from "@/components/quiz/shared/choices-bank"
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
import { useMatching } from "@/hooks/quiz/use-matching"
import { QUIZ_INSTRUCTIONS, ValidationStatus } from "@/types/enums"
import type { MatchingItem, MatchingModel } from "@/types/models"

type DragNDropProps = {
	item: MatchingModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

export default function Matching({
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
	} = useMatching(item, { forceValidation })

	useEffect(() => {
		if (showValidation && onScore) {
			onScore(correctAnswersCount, totalScore)
		}
	}, [showValidation, onScore, correctAnswersCount, totalScore])

	const choicesBank = (
		<ChoicesBank
			values={availableValues}
			disabled={showValidation}
			chipId={(item) => `chip-${item.id}`}
			imageUrl={(item) => item.asset_url}
			displayValue={(value) => value.text}
			emptyMessage="Όλα τα αντικείμενα έχουν τοποθετηθεί"
		/>
	)

	return (
		<QuizDndProvider<MatchingItem>
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
				{item.content.prompt_text && (
					<p className="mb-3 text-sm font-medium">{item.content.prompt_text}</p>
				)}
				<div className="overflow-x-auto rounded-xl border">
					<Table className="table-fixed w-full">
						<TableHeader>
							<TableRow>
								{item.content.columns.map((column, index) => (
									<TableHead
										key={`column-${index}-${column.title}`}
										className={`w-28 sm:w-48 border-b text-center text-xs sm:text-sm font-semibold p-1 sm:p-2 ${
											index !== 0 ? "border-l" : ""
										}`}
									>
										{column.title || (index === 0 ? "ΣΤΗΛΗ Ι" : "ΣΤΗΛΗ ΙΙ")}
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
									{item.content.columns.map((_column, colIndex) => {
										const cellValue = tableValues[rowIndex][colIndex]

										const validationState = getCellValidationState(
											rowIndex,
											colIndex,
										)

										const correctValue =
											colIndex === 1 ? getCorrectValue(rowIndex) : null

										return (
											<TableCell
												key={`cell-${rowIndex}-${colIndex}`}
												className={colIndex !== 0 ? "border-l" : ""}
											>
												<div className="flex flex-col gap-1">
													<DroppableCell
														id={`droppableCell-${rowIndex}-${colIndex}`}
														imageUrl={cellValue?.asset_url}
														value={cellValue}
														displayValue={(value) => value.text}
														disabled={Boolean(cellValue)}
														validationState={validationState}
														isLocked={showValidation || colIndex === 0}
														onRemove={() => clearCell(rowIndex, colIndex)}
													/>
													{validationState === ValidationStatus.Incorrect &&
														correctValue && (
															<DroppableCell
																id={`correctCell-${rowIndex}-${colIndex}`}
																imageUrl={correctValue.asset_url}
																value={correctValue}
																displayValue={(value) => value.text}
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
