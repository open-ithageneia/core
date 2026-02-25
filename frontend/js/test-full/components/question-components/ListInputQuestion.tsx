import { Input } from "@/components/ui/input"
import type { FullListInputQuestion } from "../../types/Full.types"

// value schema: ["Αττικής", "Κρήτης", "", ""] Array σταθερού μήκους (maxItems) Κάθε index αντιστοιχεί σε μία αριθμημένη γραμμή απάντησης.
type Props = {
	question: FullListInputQuestion
	value?: string[]
	onChange: (value: string[]) => void
}

const ListInputQuestion = ({ question, value = [], onChange }: Props) => {
	const itemsCount = question.maxItems

	// o parent δεν ξέρει το schema της ερώτησης
	const handleChange = (index: number, val: string) => {
		const updated = [...value]
		updated[index] = val
		onChange(updated)
	}

	return (
		<div className="space-y-4">
			<p className="font-medium">{question.question}</p>

			<div className="space-y-2">
				{/* Το κάνεις για να δημιουργήσεις σταθερό αριθμό inputs με βάση maxItems. Δεν βασίζεσαι στο value.length, γιατί: Θες πάντα π.χ. 4 πεδία Ακόμα κι αν ο χρήστης έχει συμπληρώσει μόνο 1 */}
				{Array.from({ length: itemsCount }).map((_, index) => {
					const inputKey = `list-input-${index}`

					return (
						<div key={inputKey} className="flex items-center gap-2">
							<div className="w-6 text-sm font-semibold">{index + 1}.</div>
							{/* Input → εισαγωγή γραπτού κειμένου */}
							<Input
								value={value[index] ?? ""}
								onChange={(e) => handleChange(index, e.target.value)}
								placeholder="γράψε απάντηση"
							/>
						</div>
					)
				})}
			</div>
		</div>
	)
}

export default ListInputQuestion

/*
	{
		"id": "GEO_6",
		"category": "γεωγραφία",
		"type": "listInput",
		"question": "Γράψτε τέσσερις (4) από τις δεκατρείς (13) Διοικητικές Περιφέρειες της Ελλάδας.",
		"minItems": 4,
		"maxItems": 4,
		"correctAnswer": [
			"Ανατολικής Μακεδονίας και Θράκης",
			"Αττικής",
			"Βορείου Αιγαίου",
			"Δυτικής Ελλάδας",
			"Δυτικής Μακεδονίας",
			"Ηπείρου",
			"Θεσσαλίας",
			"Ιονίων Νήσων",
			"Κεντρικής Μακεδονίας",
			"Κρήτης",
			"Νοτίου Αιγαίου",
			"Πελοποννήσου",
			"Στερεάς Ελλάδας"
		]
	},
*/
