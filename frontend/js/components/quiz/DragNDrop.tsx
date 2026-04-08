import { DragDropProvider, useDraggable, useDroppable } from "@dnd-kit/react"
import { X } from "lucide-react"
import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table"

type ContentGroup = {
	title: string
	values: string[]
}

type DragNDropItem = {
	content: ContentGroup[]
}

type DragNDropProps = {
	item: DragNDropItem
}

type CellValue = string | null

enum ValidationStatus {
	Correct = "correct",
	Incorrect = "incorrect",
}

type ValidationState = ValidationStatus | null

function shuffleArray<T>(array: T[]): T[] {
	const newArray = [...array]

	for (let i = newArray.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1))
		;[newArray[i], newArray[j]] = [newArray[j], newArray[i]]
	}

	return newArray
}

function DraggableChip({
	value,
	disabled,
}: {
	value: string
	disabled: boolean
}) {
	const { ref, isDragging } = useDraggable({
		id: value,
		disabled,
		data: { value },
	})

	return (
		<button
			ref={ref}
			type="button"
			disabled={disabled}
			className={`touch-none ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
			style={{ opacity: isDragging ? 0.45 : 1 }}
		>
			<Badge
				variant="secondary"
				className="pointer-events-none cursor-inherit rounded-full px-3 py-1 text-sm font-medium"
			>
				{value}
			</Badge>
		</button>
	)
}

function DroppableCell({
	id,
	value,
	onRemove,
	disabled,
	validationState,
	isLocked,
}: {
	id: string
	value: string | null
	onRemove: () => void
	disabled: boolean
	validationState: ValidationState
	isLocked: boolean
}) {
	const { ref, isDropTarget } = useDroppable({
		id,
		disabled: disabled || isLocked,
	})

	const isActiveDropTarget = isDropTarget && !disabled && !isLocked

	const stateClasses =
		validationState === ValidationStatus.Correct
			? "border-green-500/60 bg-green-500/5"
			: validationState === ValidationStatus.Incorrect
				? "border-red-500/60 bg-red-500/5"
				: disabled || isLocked
					? "border-muted-foreground/5 bg-muted/40"
					: isActiveDropTarget
						? "border-primary/60 bg-primary/5"
						: "border-muted-foreground/25 bg-background"

	return (
		<div
			ref={ref}
			className={`flex min-h-14 items-center justify-center rounded-lg border-2 border-dashed p-2 transition-colors ${stateClasses}`}
		>
			{value ? (
				<div className="flex items-center gap-2">
					<Badge variant="outline" className="rounded-full px-3 py-1 text-sm">
						{value}
					</Badge>

					{!isLocked ? (
						<button
							type="button"
							onClick={onRemove}
							className="rounded-full p-1 hover:bg-muted"
							aria-label={`Remove ${value}`}
						>
							<X className="h-4 w-4 cursor-pointer" />
						</button>
					) : null}
				</div>
			) : (
				<span className="text-sm text-muted-foreground">
					{isLocked ? "Κλειδωμένο" : ""}
				</span>
			)}
		</div>
	)
}

export default function DragNDrop({ item }: DragNDropProps) {
	const initialValues = useMemo(() => {
		const allValues = item.content.flatMap((group) => group.values)
		return shuffleArray(allValues)
	}, [item])

	const maxRows = Math.max(...item.content.map((group) => group.values.length))
	const columnCount = item.content.length

	const [availableValues, setAvailableValues] =
		useState<string[]>(initialValues)

	const [tableValues, setTableValues] = useState<CellValue[][]>(
		Array.from({ length: maxRows }, () =>
			Array.from({ length: columnCount }, () => null),
		),
	)

	const [showValidation, setShowValidation] = useState(false)

	// const isLocked = showValidation

	function returnValueToAvailable(value: string) {
		setAvailableValues((prevAvailableValues) => [...prevAvailableValues, value])
	}

	function removeValueFromAvailable(value: string) {
		setAvailableValues((prevAvailableValues) =>
			prevAvailableValues.filter((availableValue) => availableValue !== value),
		)
	}

	function placeValueInCell(rowIndex: number, colIndex: number, value: string) {
		if (showValidation) return
		if (tableValues[rowIndex][colIndex]) return

		setTableValues((prevTableValues) => {
			const newTableValues = prevTableValues.map((row) => [...row])
			newTableValues[rowIndex][colIndex] = value
			return newTableValues
		})

		removeValueFromAvailable(value)
	}

	function clearCell(rowIndex: number, colIndex: number) {
		if (showValidation) return

		const value = tableValues[rowIndex][colIndex]
		if (!value) return

		setTableValues((prevTableValues) => {
			const newTableValues = prevTableValues.map((row) => [...row])
			newTableValues[rowIndex][colIndex] = null
			return newTableValues
		})

		returnValueToAvailable(value)
	}

	function isValueCorrectForColumn(colIndex: number, value: string | null) {
		if (!value) return false

		return item.content[colIndex].values.includes(value)
	}

	const isTableComplete = useMemo(() => {
		return tableValues.every((row) => row.every((cell) => cell !== null))
	}, [tableValues])

	const correctAnswersCount = useMemo(() => {
		return tableValues.reduce((count, row) => {
			return (
				count +
				row.filter((cellValue, colIndex) =>
					cellValue ? item.content[colIndex].values.includes(cellValue) : false,
				).length
			)
		}, 0)
	}, [tableValues, item])

	return (
		<Card className="w-full rounded-2xl shadow-sm">
			<CardHeader>
				<CardTitle>Drag and Drop</CardTitle>
			</CardHeader>

			<CardContent className="space-y-6">
				<DragDropProvider
					onDragEnd={({ operation }) => {
						if (showValidation) return
						if (!operation.source || !operation.target) return

						const draggedValue = String(operation.source.id)
						const targetId = String(operation.target.id) // cell-{rowIndex}-{colIndex}

						if (!targetId.startsWith("cell-")) return

						const [, rowIndexString, colIndexString] = targetId.split("-")
						const rowIndex = Number(rowIndexString)
						const colIndex = Number(colIndexString)

						if (tableValues[rowIndex][colIndex]) return

						placeValueInCell(rowIndex, colIndex, draggedValue)
					}}
				>
					<div className="rounded-xl border bg-muted/30 p-4">
						<div className="flex flex-wrap gap-2">
							{availableValues.map((value) => (
								<DraggableChip
									key={value}
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
										// biome-ignore lint/suspicious/noArrayIndexKey: Till we fix this
										key={rowIndex}
										className={rowIndex % 2 === 0 ? "bg-muted/20" : ""}
									>
										{item.content.map((group, colIndex) => {
											const cellValue = tableValues[rowIndex][colIndex]

											const validationState: ValidationState =
												showValidation && cellValue
													? isValueCorrectForColumn(colIndex, cellValue)
														? ValidationStatus.Correct
														: ValidationStatus.Incorrect
													: null

											return (
												<TableCell
													// biome-ignore lint/suspicious/noArrayIndexKey: Till we fix this
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
						<div className="flex flex-col items-center justify-center gap-2">
							<Button
								type="button"
								onClick={() => setShowValidation(true)}
								disabled={showValidation}
							>
								{showValidation
									? "Οι απαντήσεις ελέγχθηκαν"
									: "Έλεγχος απαντήσεων"}
							</Button>

							{showValidation && (
								<p className="text-sm text-muted-foreground">
									Score: {correctAnswersCount} / {maxRows * columnCount}
								</p>
							)}
						</div>
					)}
				</DragDropProvider>
			</CardContent>
		</Card>
	)
}
