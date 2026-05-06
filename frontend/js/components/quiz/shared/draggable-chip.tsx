import { useDraggable } from "@dnd-kit/react"

import { Badge } from "@/components/ui/badge"

type DraggableChipProps = {
	id: string
	value: string
	disabled: boolean
}

export default function DraggableChip({
	id,
	value,
	disabled,
}: DraggableChipProps) {
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
				{value}
			</Badge>
		</button>
	)
}
