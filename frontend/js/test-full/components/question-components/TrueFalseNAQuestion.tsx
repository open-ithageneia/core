import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import type { FullTrueFalseNAQuestion } from "../../types/Full.types"

// value schema: "T" | "F" | "NA" Απλό string union. Δεν είναι object όπως στο trueFalseGroup.
type Props = {
	question: FullTrueFalseNAQuestion
	value?: string
	onChange: (value: "T" | "F" | "NA") => void
}

const TrueFalseNAQuestion = ({ question, value, onChange }: Props) => {
	return (
		<div className="space-y-2">
			<p className="font-medium">{question.question}</p>

			<RadioGroup
				value={value ?? ""}
				onValueChange={(v) => {
					if (v === "T" || v === "F" || v === "NA") {
						onChange(v)
					}
				}}
			>
				<div className="flex items-center gap-2">
					<RadioGroupItem value="T" id={`${question.id}-t`} />
					<Label htmlFor={`${question.id}-t`}>Σωστό</Label>
				</div>

				<div className="flex items-center gap-2">
					<RadioGroupItem value="F" id={`${question.id}-f`} />
					<Label htmlFor={`${question.id}-f`}>Λάθος</Label>
				</div>

				<div className="flex items-center gap-2">
					<RadioGroupItem value="NA" id={`${question.id}-na`} />
					<Label htmlFor={`${question.id}-na`}>Δεν αναφέρεται</Label>
				</div>
			</RadioGroup>
		</div>
	)
}

export default TrueFalseNAQuestion

/*
{
  "id": "LANG_TEST_1_A_6",
  "type": "trueFalseNA",
  "question": "Οι ηλεκτρονικές συναλλαγές περιορίζουν τις επιλογές μας",
  "correctAnswer": "F",
  "category": "γλώσσα"
},
*/
