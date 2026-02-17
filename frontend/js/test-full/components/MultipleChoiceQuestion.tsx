// frontend\src\test-full\components\MultipleChoiceQuestion.tsx
// component για multiple choice ερώτηση

import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import type { FullMultipleChoiceQuestion } from "../types/Full.types"
import QuestionMediaBlock from "./QuestionMediaBlock"

type Props = {
	question: FullMultipleChoiceQuestion
	value: string | undefined
	onChange: (value: string) => void
}

const MultipleChoiceQuestion = ({ question, value, onChange }: Props) => {
	return (
		<div className="space-y-3">
			<p className="font-medium">{question.question}</p>

			{question.media && <QuestionMediaBlock media={question.media} />}

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
