import { DragDropProvider, useDraggable, useDroppable } from "@dnd-kit/react"
import { Magnet, X } from "lucide-react"
import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
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

function shuffleArray<T>(array: T[]): T[] {
	const newArray = [...array]

	for (let i = newArray.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1))
		;[newArray[i], newArray[j]] = [newArray[j], newArray[i]]
	}

	return newArray
}

function DraggableChip({ value }: { value: string }) {
	const { ref, isDragging } = useDraggable({
		id: value,
		data: { value },
	})

	return (
		<button
			ref={ref}
			type="button"
			className="touch-none cursor-pointer"
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
}: {
	id: string
	value: string | null
	onRemove: () => void
}) {
	const { ref, isDropTarget } = useDroppable({
		id,
	})

	return (
		<div
			ref={ref}
			className={`flex min-h-14 items-center justify-center rounded-lg border-2 border-dashed bg-background p-2 transition-colors ${
				isDropTarget
					? "border-primary/60 bg-primary/5"
					: "border-muted-foreground/25"
			}`}
		>
			{value ? (
				<div className="flex items-center gap-2">
					<Badge variant="outline" className="rounded-full px-3 py-1 text-sm">
						{value}
					</Badge>

					<button
						type="button"
						onClick={onRemove}
						className="rounded-full p-1 hover:bg-muted"
						aria-label={`Remove ${value}`}
					>
						<X className="h-4 w-4" />
					</button>
				</div>
			) : (
				<span className="text-sm text-muted-foreground" />
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

	function returnValueToAvailable(value: string) {
		setAvailableValues((prevAvailableValues) => [...prevAvailableValues, value])
	}

	return (
		<Card className="w-full rounded-2xl shadow-sm">
			<CardHeader>
				<CardTitle>Drag and Drop</CardTitle>
			</CardHeader>

			<CardContent className="space-y-6">
				<DragDropProvider
					onDragEnd={({ operation }) => {
						if (!operation.source || !operation.target) return

						const draggedValue = String(operation.source.id)
						const targetId = String(operation.target.id) // cell-{rowIndex}-{colIndex}

						if (!targetId.startsWith("cell-")) return

						const [, rowIndexString, colIndexString] = targetId.split("-")
						const rowIndex = Number(rowIndexString)
						const colIndex = Number(colIndexString)

						// add draggedValue to current cell with targetId
						setTableValues((prevTableValues) => {
							const newTableValues = prevTableValues.map((row) => [...row]) // clone
							const existingValue = newTableValues[rowIndex][colIndex]

							if (existingValue) {
								returnValueToAvailable(existingValue)
							}

							newTableValues[rowIndex][colIndex] = draggedValue

							return newTableValues
						})

						// remove draggedValue from list
						setAvailableValues((prevAvailableValues) =>
							prevAvailableValues.filter((value) => value !== draggedValue),
						)
					}}
				>
					<div className="rounded-xl border bg-muted/30 p-4">
						<div className="flex flex-wrap gap-2">
							{availableValues.map((value) => (
								<DraggableChip key={value} value={value} />
							))}
						</div>
					</div>

					<div className="overflow-x-auto rounded-xl border">
						<Table>
							<TableHeader>
								<TableRow>
									{item.content.map((group, index) => (
										<TableHead
											key={group.title}
											className={`border-b text-center font-semibold ${
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
										{item.content.map((group, colIndex) => (
											<TableCell
												// biome-ignore lint/suspicious/noArrayIndexKey: Till we fix this
												key={`${group.title}-${rowIndex}`}
												className={colIndex !== 0 ? "border-l" : ""}
											>
												<DroppableCell
													id={`cell-${rowIndex}-${colIndex}`}
													value={tableValues[rowIndex][colIndex]}
													onRemove={() => {
														const value = tableValues[rowIndex][colIndex]
														if (!value) return

														setTableValues((prevTableValues) => {
															const newTableValues = prevTableValues.map(
																(row) => [...row],
															)
															newTableValues[rowIndex][colIndex] = null
															return newTableValues
														})

														returnValueToAvailable(value)
													}}
												/>
											</TableCell>
										))}
									</TableRow>
								))}
							</TableBody>
						</Table>
					</div>
				</DragDropProvider>
			</CardContent>
		</Card>
	)
}
