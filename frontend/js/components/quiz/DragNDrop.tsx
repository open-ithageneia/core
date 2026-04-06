import {
	DragDropProvider,
	DragOverlay,
	useDraggable,
	useDroppable,
} from "@dnd-kit/react"
import { X } from "lucide-react"
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
			className="touch-none"
			style={{ opacity: isDragging ? 0.45 : 1 }}
		>
			<Badge
				variant="secondary"
				className="rounded-full px-3 py-1 text-sm font-medium"
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
	const [activeValue, setActiveValue] = useState<string | null>(null)
	const [placedValues, setPlacedValues] = useState<CellValue[][]>(
		Array.from({ length: maxRows }, () =>
			Array.from({ length: columnCount }, () => null),
		),
	)

	function returnValueToSource(value: string) {
		setAvailableValues((prev) => [...prev, value])
	}

	return (
		<DragDropProvider
			onDragStart={({ source }) => {
				setActiveValue(String(source.id))
			}}
			onDragEnd={({ source, target }) => {
				setActiveValue(null)

				if (!target) return

				const draggedValue = String(source.id)
				const targetId = String(target.id)

				if (!targetId.startsWith("cell-")) return

				const [, rowIndexString, colIndexString] = targetId.split("-")
				const rowIndex = Number(rowIndexString)
				const colIndex = Number(colIndexString)

				if (Number.isNaN(rowIndex) || Number.isNaN(colIndex)) return

				setPlacedValues((prev) => {
					const next = prev.map((row) => [...row])
					const existingValue = next[rowIndex][colIndex]

					if (existingValue) {
						returnValueToSource(existingValue)
					}

					next[rowIndex][colIndex] = draggedValue
					return next
				})

				setAvailableValues((prev) =>
					prev.filter((value) => value !== draggedValue),
				)
			}}
			onDragCancel={() => {
				setActiveValue(null)
			}}
		>
			<Card className="w-full rounded-2xl shadow-sm">
				<CardHeader>
					<CardTitle>Drag and Drop</CardTitle>
				</CardHeader>

				<CardContent className="space-y-6">
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
										key={rowIndex}
										className={rowIndex % 2 === 0 ? "bg-muted/20" : ""}
									>
										{item.content.map((group, colIndex) => (
											<TableCell
												key={`${group.title}-${rowIndex}`}
												className={colIndex !== 0 ? "border-l" : ""}
											>
												<DroppableCell
													id={`cell-${rowIndex}-${colIndex}`}
													value={placedValues[rowIndex][colIndex]}
													onRemove={() => {
														const value = placedValues[rowIndex][colIndex]
														if (!value) return

														setPlacedValues((prev) => {
															const next = prev.map((row) => [...row])
															next[rowIndex][colIndex] = null
															return next
														})

														returnValueToSource(value)
													}}
												/>
											</TableCell>
										))}
									</TableRow>
								))}
							</TableBody>
						</Table>
					</div>
				</CardContent>
			</Card>

			<DragOverlay>
				{activeValue ? (
					<Badge
						variant="secondary"
						className="rounded-full px-3 py-1 text-sm font-medium shadow-md"
					>
						{activeValue}
					</Badge>
				) : null}
			</DragOverlay>
		</DragDropProvider>
	)
}
