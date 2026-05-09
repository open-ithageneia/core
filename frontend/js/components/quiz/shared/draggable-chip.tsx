import { useDraggable } from "@dnd-kit/react"

import { Badge } from "@/components/ui/badge"

type DraggableChipProps<T> = {
	id: string
	value: T
	displayValue?: (value: T) => string | null
	disabled: boolean
}

export default function DraggableChip<T>({
	id,
	value,
	displayValue = (v: T) => String(v),
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
				className="pointer-events-none cursor-inherit rounded-full px-3 py-1 text-sm font-medium"
			>
				{displayValue(value)}
			</Badge>
		</button>
	)
}
