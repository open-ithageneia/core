import { Checkbox } from "@/components/ui/checkbox"
import type { FullMultiSelectQuestion } from "../types/Full.types"
import QuestionMediaBlock from "./QuestionMediaBlock"

type Props = {
	question: FullMultiSelectQuestion
	value?: string[]
	onChange: (value: string[]) => void
}

const MultiSelectQuestion = ({ question, value = [], onChange }: Props) => {
	const handleToggle = (option: string) => {
		const current = value ?? []

		const alreadySelected = current.includes(option)

		if (alreadySelected) {
			onChange(current.filter((o) => o !== option))
			return
		}

		// Αν φτάσαμε maxSelections δεν προσθέτουμε άλλο
		if (current.length >= question.maxSelections) return

		onChange([...current, option])
	}

	return (
		<div className="space-y-4">
			<p className="font-medium whitespace-pre-line">{question.question}</p>

			{question.media && question.media.length > 0 && (
				<QuestionMediaBlock media={question.media} />
			)}

			<div className="space-y-2">
				{question.options.map((option) => {
					const id = `multi-${question.id}-${option}`

					return (
						<div key={option} className="flex items-center space-x-2">
							<Checkbox
								id={id}
								checked={value.includes(option)}
								onCheckedChange={() => handleToggle(option)}
							/>
							<label htmlFor={id} className="text-sm font-medium">
								{option}
							</label>
						</div>
					)
				})}
			</div>

			<p className="text-xs text-muted-foreground">
				Επιλέξτε {question.minSelections} έως {question.maxSelections}.
			</p>
		</div>
	)
}

export default MultiSelectQuestion
