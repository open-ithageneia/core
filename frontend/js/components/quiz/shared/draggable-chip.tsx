import { useDraggable } from "@dnd-kit/react"

import { Badge } from "@/components/ui/badge"

type DraggableChipProps<T> = {
	id: string
	value: T
	displayValue?: (value: T) => string | null
	imageUrl?: string | null
	disabled: boolean
}

export default function DraggableChip<T>({
	id,
	value,
	displayValue = (v: T) => String(v),
	imageUrl,
	disabled,
}: DraggableChipProps<T>) {
	const { ref, isDragging } = useDraggable({
		id,
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
				className="pointer-events-none cursor-inherit rounded-2xl px-2 py-1 text-sm font-medium"
			>
				{imageUrl ? (
					<img src={imageUrl} alt={`Επιλογή ${id}`} className="rounded" />
				) : (
					displayValue(value)
				)}
			</Badge>
		</button>
	)
}
