// frontend\src\test-full\components\MultipleChoiceQuestion.tsx
// component για multiple choice ερώτηση
// Δεν κρατά state — όλο το state διαχειρίζεται από το parent (PagePicker).

import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import type { FullMultipleChoiceQuestion } from "../../types/Full.types"
import QuestionMediaBlock from "../QuestionMediaBlock"

// value schema: "A"  όπου value = το key της επιλογής (πχ "A", "B", "C", "D")
type Props = {
	question: FullMultipleChoiceQuestion
	value: string | undefined
	onChange: (value: string) => void
}

const MultipleChoiceQuestion = ({ question, value, onChange }: Props) => {
	return (
		<div className="space-y-3">
			<p className="font-medium whitespace-pre-line">{question.question}</p>

			{/* ενας renderer μιας η περισσοτερων εικονων. είναι έτσι σε πολλα components που είναι πιθανό να έχουν πεδία question.media */}
			{question.media && <QuestionMediaBlock media={question.media} />}

			<RadioGroup value={value} onValueChange={onChange}>
				{/* Δεν μπορείς να κάνεις map απευθείας γιατί είναι object, όχι array. Αν έχεις: options: {  A: 'Αθήνα',  B: 'Ρώμη' } Τότε: key → "A", option → "Αθήνα" */}
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

/*
	{
		"id": "CULT_1",
		"category": "πολιτισμός",
		"active": true,
		"type": "multipleChoice",
		"question": "Σύμφωνα με την ελληνική μυθολογία δύο θεοί του Ολύμπου διεκδίκησαν την προστασία της πόλεως των Αθηνών. Ποιοι ήταν οι θεοί αυτοί;",
		"options": {
			"A": "Η Αθηνά και η Δήμητρα",
			"B": "Η Αθηνά και ο Ποσειδώνας",
			"C": "Η Αθηνά και ο Άρης",
			"D": "Η Αθηνά και η Αφροδίτη"
		},
		"correctAnswer": "B"
	},
*/
