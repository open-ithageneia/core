import { useDroppable } from "@dnd-kit/react"
import { X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { ValidationStatus } from "@/types/enums"
import type { ValidationState } from "@/types/quiz"

type DroppableCellProps = {
	id: string
	value: string | null
	onRemove: () => void
	disabled: boolean
	validationState: ValidationState
	isLocked: boolean
}

export default function DroppableCell({
	id,
	value,
	onRemove,
	disabled,
	validationState,
	isLocked,
}: DroppableCellProps) {
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
			className={`flex min-w-16 sm:min-w-30 min-h-8 sm:min-h-14 items-center justify-center rounded-lg border-2 border-dashed p-1 sm:p-2 transition-colors ${stateClasses}`}
		>
			{value ? (
				<div className="flex items-center gap-2">
					<Badge variant="outline" className="rounded-full px-3 py-1 text-sm text-center break-words whitespace-normal">
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
					{isLocked ? "---" : ""}
				</span>
			)}
		</div>
	)
}
