import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import type { FullTrueFalseGroupQuestion } from "../../types/Full.types"
import QuestionMediaBlock from "../QuestionMediaBlock"

// value schema: { "1": "T", "2": "F", "3": "T" } όπου key = statement.key
// value = "T" | "F" Δεν αποθηκεύεται "Σ"/"Λ" αλλά normalized internal values ("T"/"F")
type Props = {
	question: FullTrueFalseGroupQuestion
	value?: Record<string, "T" | "F">
	onChange: (value: Record<string, "T" | "F">) => void
}

const TrueFalseGroupQuestion = ({ question, value = {}, onChange }: Props) => {
	// o parent δεν γνωρίζει schema κάθε ερώτησης
	const handleChange = (key: string, val: "T" | "F") => {
		onChange({
			...value,
			[key]: val,
		})
	}

	return (
		<div className="space-y-4">
			{/* εκφώνηση */}
			<p className="font-medium">{question.question}</p>

			{/* ενας renderer μιας η περισσοτερων εικονων. είναι έτσι σε πολλα components που είναι πιθανό να έχουν πεδία question.media */}
			{question.media && question.media.length > 0 && (
				<QuestionMediaBlock media={question.media} />
			)}

			<div className="space-y-4">
				{question.statements.map((statement) => (
					<div key={statement.key} className="space-y-2 border p-3 rounded">
						<p className="font-medium">
							{statement.key}. {statement.text}
						</p>

						{/* Κάθε statement έχει ανεξάρτητο RadioGroup. (είμαστε μέσα στο map) */}
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

/*
	{
		"id": "CULT_13",
		"category": "πολιτισμός",
		"active": true,
		"type": "trueFalseGroup",
		"question": "Να σημειώσετε Σ, αν η πρόταση είναι σωστή, ή Λ, αν είναι λάθος.",
		"statements": [
			{
				"key": "1",
				"text": "O Αυτοκράτορας Θεοδόσιος έκτισε τα πρώτα τείχη της Κωνσταντινουπόλεως"
			},
			{
				"key": "2",
				"text": "Ο Αυτοκράτορας Ιουστινιανός ανήγειρε τον Ιππόδρομο της Κωνσταντινουπόλεως."
			},
			{
				"key": "3",
				"text": "Ο Ιερός Ναός της Αγίας Σοφίας ανεγέρθη επί Αυτοκράτορα Ιουστινιανού."
			},
			{
				"key": "4",
				"text": "Ο Ιερός Ναός της Αγίας Ειρήνης στην Κωνσταντινούπολη κτίστηκε από τον Μεγάλο Κωνσταντίνο."
			}
		],
		"correctAnswer": { "1": "F", "2": "F", "3": "T", "4": "T" }
	},

	{
		"id": "CULT_31",
		"category": "πολιτισμός",
		"active": true,
		"type": "trueFalseGroup",
		"question": "Ποια από τα εικονιζόμενα κτήρια είναι στο πνεύμα του Νεοκλασικισμού;",
		"media": [
			{
				"id": "1",
				"type": "image",
				"src": "test-full/media/culture/31a.jpg",
				"alt": "Εικ. 1"
			},
			{
				"id": "2",
				"type": "image",
				"src": "test-full/media/culture/31b.jpg",
				"alt": "Εικ. 2"
			},
			{
				"id": "3",
				"type": "image",
				"src": "test-full/media/culture/31c.jpg",
				"alt": "Εικ. 3"
			},
			{
				"id": "4",
				"type": "image",
				"src": "test-full/media/culture/31d.jpg",
				"alt": "Εικ. 4"
			}
		],
		"statements": [
			{ "key": "1", "text": "Εικ. 1" },
			{ "key": "2", "text": "Εικ. 2" },
			{ "key": "3", "text": "Εικ. 3" },
			{ "key": "4", "text": "Εικ. 4" }
		],
		"correctAnswer": {
			"1": "F",
			"2": "T",
			"3": "T",
			"4": "F"
		}
	},  
*/
