import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { FullOpenTextQuestion } from "../types/Full.types"

type Props = {
	question: FullOpenTextQuestion
	value?: string
	onChange: (value: string) => void
}

const OpenTextQuestion = ({ question, value = "", onChange }: Props) => {
	const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0

	const isOverLimit = wordCount > question.maxWords

	return (
		<div className="space-y-2">
			<Label className="font-medium">{question.question}</Label>

			<Textarea
				value={value}
				onChange={(e) => onChange(e.target.value)}
				className={isOverLimit ? "border-red-500" : ""}
				rows={6}
			/>

			<div className="text-sm text-muted-foreground">
				Λέξεις: {wordCount} / {question.maxWords}
			</div>

			{isOverLimit && (
				<div className="text-sm text-red-500">
					Έχετε υπερβεί το όριο λέξεων.
				</div>
			)}
		</div>
	)
}

export default OpenTextQuestion
