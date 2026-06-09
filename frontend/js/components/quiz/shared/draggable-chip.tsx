import { useDraggable } from "@dnd-kit/react"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

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
			className={cn(
				"draggable-chip-hold shrink-0 touch-manipulation select-none rounded-2xl",
				disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
				isDragging &&
					"scale-108 shadow-[0_0_0_3px_color-mix(in_oklch,var(--primary)_40%,transparent)]",
			)}
			style={{ opacity: isDragging ? 0.45 : 1 }}
		>
			<Badge
				variant="secondary"
				className="pointer-events-none cursor-inherit rounded-2xl px-2 py-1 text-sm font-medium"
			>
				{imageUrl ? (
					<img
						src={imageUrl}
						alt={`Επιλογή ${id}`}
						className="max-h-48 rounded"
					/>
				) : (
					displayValue(value)
				)}
			</Badge>
		</button>
	)
}
