// frontend\src\languageTest\components\test-parts\MultipleChoiceQuestion.tsx
// component για multiple choice ερώτηση

import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"

type Props = {
	question: {
		id: string
		question: string
		options: Record<string, string>
	}
	value: string | undefined
	onChange: (value: string) => void
}

const MultipleChoiceQuestion = ({ question, value, onChange }: Props) => {
	return (
		<div className="space-y-3">
			<p className="font-medium">{question.question}</p>

			<RadioGroup value={value} onValueChange={onChange}>
				{Object.entries(question.options).map(([key, option]) => (
					<div key={key} className="flex items-center space-x-2">
						<RadioGroupItem value={key} id={`${question.id}_${key}`} />
						<Label htmlFor={`${question.id}_${key}`}>
							{key}. {option}
						</Label>
					</div>
				))}
			</RadioGroup>
		</div>
	)
}

export default MultipleChoiceQuestion
