import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select"
import type { FullCategorizationQuestion } from "../../types/Full.types"

// value schema: { "Κερκίνη": "II", "Αλιάκμονας": "I" }
type Props = {
	question: FullCategorizationQuestion
	value?: Record<string, string>
	onChange: (value: Record<string, string>) => void
}

const CategorizationQuestionComponent = ({
	question,
	value = {},
	onChange,
}: Props) => {
	const handleSelect = (item: string, categoryKey: string) => {
		onChange({
			...value,
			[item]: categoryKey,
		})
	}

	return (
		<div className="space-y-4">
			{/* εκφώνηση */}
			<p className="font-medium">{question.question}</p>

			<div className="space-y-3">
				{question.items.map((item) => (
					<div key={item} className="flex items-center gap-4">
						<span className="w-48 font-semibold">{item}</span>

						<Select
							value={value[item] ?? ""}
							onValueChange={(val) => handleSelect(item, val)}
						>
							<SelectTrigger className="w-56">
								<SelectValue placeholder="Επιλογή κατηγορίας" />
							</SelectTrigger>

							<SelectContent>
								{question.categories.map((cat) => (
									<SelectItem key={cat.key} value={cat.key}>
										{cat.label}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
				))}
			</div>
		</div>
	)
}

export default CategorizationQuestionComponent

/*
	{
		"id": "GEO_44",
		"category": "γεωγραφία",
		"type": "categorization",
		"question": "Κατατάξτε κάθε ποταμό στη Στήλη I: Ποταμοί και κάθε λίμνη στη Στήλη II: Λίμνες.",
		"categories": [
			{ "key": "I", "label": "Ποταμοί" },
			{ "key": "II", "label": "Λίμνες" }
		],
		"items": [
			"Κερκίνη",
			"Αλιάκμονας",
			"Τριχωνίδα",
			"Πηνειός",
			"Έβρος",
			"Βιστωνίδα",
			"Κορώνεια",
			"Αχελώος"
		],
		"correctAnswer": {
			"I": ["Αλιάκμονας", "Πηνειός", "Έβρος", "Αχελώος"],
			"II": ["Κερκίνη", "Τριχωνίδα", "Βιστωνίδα", "Κορώνεια"]
		}
	},
*/
