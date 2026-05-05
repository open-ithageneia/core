import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

export type MultiSelectOption = {
	value: string
	label: string
}

type MultiSelectProps = {
	options: MultiSelectOption[]
	selected: string[]
	onChange: (selected: string[]) => void
	placeholder?: string
	className?: string
}

export function MultiSelect({
	options,
	selected,
	onChange,
	placeholder = "Επιλέξτε...",
	className,
}: MultiSelectProps) {
	const [open, setOpen] = useState(false)
	const containerRef = useRef<HTMLDivElement>(null)

	useEffect(() => {
		function handleClickOutside(e: MouseEvent) {
			if (
				containerRef.current &&
				!containerRef.current.contains(e.target as Node)
			) {
				setOpen(false)
			}
		}
		document.addEventListener("mousedown", handleClickOutside)
		return () => document.removeEventListener("mousedown", handleClickOutside)
	}, [])

	function toggle(value: string) {
		if (selected.includes(value)) {
			onChange(selected.filter((v) => v !== value))
		} else {
			onChange([...selected, value])
		}
	}

	const selectedLabels = selected
		.map((v) => options.find((o) => o.value === v)?.label)
		.filter(Boolean)

	return (
		<div ref={containerRef} className={cn("relative", className)}>
			<button
				type="button"
				onClick={() => setOpen((o) => !o)}
				className="flex w-full items-center justify-between rounded-lg border border-gray-300 px-3 py-2 text-left text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
			>
				<span className={selected.length === 0 ? "text-gray-500" : ""}>
					{selected.length === 0 ? placeholder : selectedLabels.join(", ")}
				</span>
				<svg
					aria-hidden="true"
					className={cn(
						"ml-2 h-4 w-4 shrink-0 text-gray-400 transition-transform",
						open && "rotate-180",
					)}
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
				>
					<path
						strokeLinecap="round"
						strokeLinejoin="round"
						strokeWidth={2}
						d="M19 9l-7 7-7-7"
					/>
				</svg>
			</button>

			{open && (
				<div className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-gray-200 bg-white shadow-lg">
					{options.map((option) => (
						<label
							key={option.value}
							className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50"
						>
							<input
								type="checkbox"
								checked={selected.includes(option.value)}
								onChange={() => toggle(option.value)}
								className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
							/>
							{option.label}
						</label>
					))}
				</div>
			)}
		</div>
	)
}
