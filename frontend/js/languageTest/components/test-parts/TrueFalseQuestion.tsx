// frontend\src\languageTest\components\test-parts\TrueFalseQuestion.tsx
// component για true / false

import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"

type Props = {
	question: {
		id: string
		question: string
	}
	value: string | undefined
	onChange: (value: string) => void
}

const TrueFalseQuestion = ({ question, value, onChange }: Props) => {
	return (
		<div className="space-y-3">
			<p className="font-medium">{question.question}</p>

			<RadioGroup value={value} onValueChange={onChange}>
				<div className="flex items-center space-x-2">
					<RadioGroupItem value="T" id={`${question.id}_T`} />
					<Label htmlFor={`${question.id}_T`}>Σ (Σωστό)</Label>
				</div>

				<div className="flex items-center space-x-2">
					<RadioGroupItem value="F" id={`${question.id}_F`} />
					<Label htmlFor={`${question.id}_F`}>Λ (Λάθος)</Label>
				</div>

				<div className="flex items-center space-x-2">
					<RadioGroupItem value="NA" id={`${question.id}_NA`} />
					<Label htmlFor={`${question.id}_NA`}>Δ/Α</Label>
				</div>
			</RadioGroup>
		</div>
	)
}

export default TrueFalseQuestion
