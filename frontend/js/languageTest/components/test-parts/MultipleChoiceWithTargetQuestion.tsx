// component για multiple choice ερώτηση μέρος β2 όπου λέει δώστε συνόνημο για το υπογραμισμένο

import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"

type Props = {
	question: {
		id: string
		question: string
		options: Record<string, string>
		target?: string
	}
	value: string | undefined
	onChange: (value: string) => void
}

const MultipleChoiceWithTargetQuestion = ({
	question,
	value,
	onChange,
}: Props) => {
	const renderQuestionText = () => {
		if (!("target" in question) || !question.target) {
			return question.question
		}

		const parts = question.question.split(question.target)

		if (parts.length < 2) return question.question

		return (
			<>
				{parts[0]}
				<span className="underline font-bold text-lg ">{question.target}</span>
				{parts[1]}
			</>
		)
	}

	return (
		<div className="space-y-3">
			<p className="font-medium">{renderQuestionText()}</p>

			<RadioGroup value={value} onValueChange={onChange}>
				{Object.entries(question.options).map(([key, option]) => (
					<div
						key={`${question.id}_${key}`}
						className="flex items-center space-x-2"
					>
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

export default MultipleChoiceWithTargetQuestion
