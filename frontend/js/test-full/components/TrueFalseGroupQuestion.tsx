import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import type { FullTrueFalseGroupQuestion } from "../types/Full.types"
import QuestionMediaBlock from "./QuestionMediaBlock"

type Props = {
	question: FullTrueFalseGroupQuestion
	value?: Record<string, "T" | "F">
	onChange: (value: Record<string, "T" | "F">) => void
}

const TrueFalseGroupQuestion = ({ question, value = {}, onChange }: Props) => {
	const handleChange = (key: string, val: "T" | "F") => {
		onChange({
			...value,
			[key]: val,
		})
	}

	return (
		<div className="space-y-4">
			<p className="font-medium">{question.question}</p>

			{question.media && question.media.length > 0 && (
				<QuestionMediaBlock media={question.media} />
			)}

			<div className="space-y-4">
				{question.statements.map((statement) => (
					<div key={statement.key} className="space-y-2 border p-3 rounded">
						<p className="font-medium">
							{statement.key}. {statement.text}
						</p>

						<RadioGroup
							value={value[statement.key]}
							onValueChange={(val) =>
								handleChange(statement.key, val as "T" | "F")
							}
							className="flex gap-6"
						>
							<div className="flex items-center space-x-2">
								<RadioGroupItem value="T" id={`${statement.key}_T`} />
								<Label htmlFor={`${statement.key}_T`}>Σ</Label>
							</div>

							<div className="flex items-center space-x-2">
								<RadioGroupItem value="F" id={`${statement.key}_F`} />
								<Label htmlFor={`${statement.key}_F`}>Λ</Label>
							</div>
						</RadioGroup>
					</div>
				))}
			</div>
		</div>
	)
}

export default TrueFalseGroupQuestion
