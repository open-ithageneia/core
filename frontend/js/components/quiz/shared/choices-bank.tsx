import DraggableChip from "@/components/quiz/shared/draggable-chip"

type ChoicesBankProps<T> = {
	values: T[]
	disabled: boolean
	chipId: (value: T, index: number) => string
	chipKey?: (value: T, index: number) => string
	displayValue?: (value: T) => string | null
	imageUrl?: (value: T) => string | null | undefined
	emptyMessage?: string | null
}

export default function ChoicesBank<T>({
	values,
	disabled,
	chipId,
	chipKey,
	displayValue,
	imageUrl,
	emptyMessage = null,
}: ChoicesBankProps<T>) {
	return (
		<div className="rounded-xl border bg-muted/30 p-2">
			<div className="flex py-2 items-center gap-1 overflow-x-auto">
				{values.map((value, index) => (
					<DraggableChip
						key={chipKey ? chipKey(value, index) : chipId(value, index)}
						id={chipId(value, index)}
						value={value}
						displayValue={displayValue}
						imageUrl={imageUrl?.(value)}
						disabled={disabled}
					/>
				))}
				{values.length === 0 && !disabled && emptyMessage && (
					<span className="text-sm text-muted-foreground">{emptyMessage}</span>
				)}
			</div>
		</div>
	)
}
