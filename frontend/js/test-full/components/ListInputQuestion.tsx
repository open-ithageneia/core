import { Input } from "@/components/ui/input"
import type { FullListInputQuestion } from "../types/Full.types"

type Props = {
	question: FullListInputQuestion
	value?: string[]
	onChange: (value: string[]) => void
}

const ListInputQuestion = ({ question, value = [], onChange }: Props) => {
	const itemsCount = question.maxItems

	const handleChange = (index: number, val: string) => {
		const updated = [...value]
		updated[index] = val
		onChange(updated)
	}

	return (
		<div className="space-y-4">
			<p className="font-medium">{question.question}</p>

			<div className="space-y-2">
				{Array.from({ length: itemsCount }).map((_, index) => {
					const inputKey = `list-input-${index}`

					return (
						<div key={inputKey} className="flex items-center gap-2">
							<div className="w-6 text-sm font-semibold">{index + 1}.</div>
							<Input
								value={value[index] ?? ""}
								onChange={(e) => handleChange(index, e.target.value)}
								placeholder="γράψε απάντηση"
							/>
						</div>
					)
				})}
			</div>
		</div>
	)
}

export default ListInputQuestion
