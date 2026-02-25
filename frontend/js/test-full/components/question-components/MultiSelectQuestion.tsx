// frontend\src\test-full\components\question-components\MultiSelectQuestion.tsx
// το state διαχειρίζεται στο pagePicker, εδώ απλά γίνεται toggle και enforcement των min/max κανόνων.

import { Checkbox } from "@/components/ui/checkbox"
import type { FullMultiSelectQuestion } from "../../types/Full.types"
import QuestionMediaBlock from "../QuestionMediaBlock"

// value schema: ["B", "C"] όπου κάθε στοιχείο του array είναι option key.
type Props = {
	question: FullMultiSelectQuestion
	value?: string[]
	onChange: (value: string[]) => void
}

const MultiSelectQuestion = ({ question, value = [], onChange }: Props) => {
	// Toggle επιλογής:
	// - Αν υπάρχει → αφαιρείται
	// - Αν δεν υπάρχει → προστίθεται
	// - Αν έχει φτάσει maxSelections → αγνοείται
	// Δεν γίνεται enforcement του minSelections στο UI (μόνο ενημερωτικό). Το  το ελέγχει το grading.
	const handleToggle = (option: string) => {
		const current = value ?? []
		const alreadySelected = current.includes(option)

		if (alreadySelected) {
			onChange(current.filter((o) => o !== option))
			return
		}

		// Αν φτάσαμε maxSelections δεν προσθέτουμε άλλο
		if (current.length >= question.maxSelections) return

		onChange([...current, option])
	}

	return (
		<div className="space-y-4">
			<p className="font-medium whitespace-pre-line">{question.question}</p>

			{/* ενας renderer μιας η περισσοτερων εικονων. είναι έτσι σε πολλα components που είναι πιθανό να έχουν πεδία question.media */}
			{question.media && question.media.length > 0 && (
				<QuestionMediaBlock media={question.media} />
			)}

			<div className="space-y-2">
				{question.options.map((option) => {
					const id = `multi-${question.id}-${option}`

					// δεν χρειαζόμαστε Object.entries(...) όπως στο multiple γιατί εκεί ήταν options: { A: 'Αθήνα', B: 'Ρώμη' } ενώ εδώ options: ["A", "B", "C", "D"]. Άρα είναι ήδη array
					// εδώ έχουμε απλό label και οχι Label γιατι αν δεν κάνω λάθος έσπαγε σε mobile
					return (
						<div key={option} className="flex items-center space-x-2">
							<Checkbox
								id={id}
								checked={value.includes(option)}
								onCheckedChange={() => handleToggle(option)}
							/>
							<label htmlFor={id} className="text-sm font-medium">
								{option}
							</label>
						</div>
					)
				})}
			</div>

			<p className="text-xs text-muted-foreground">
				Επιλέξτε {question.minSelections} έως {question.maxSelections}.
			</p>
		</div>
	)
}

export default MultiSelectQuestion

/*
  {
    "id": "CULT_9",
    "category": "πολιτισμός",
    "active": true,
    "type": "multiSelect",
    "question": "Ποιες από τις φωτογραφίες ανήκουν σε έργα τέχνης του Κυκλαδικού πολιτισμού. (Μπορεί να είναι σωστές περισσότερες από μία επιλογές.)",
    "media": [
      {
        "id": "A",
        "type": "image",
        "src": "test-full/media/culture/9a.jpg",
        "alt": "Εικ. Α"
      },
      {
        "id": "B",
        "type": "image",
        "src": "test-full/media/culture/9b.jpg",
        "alt": "Εικ. Β"
      },
      {
        "id": "C",
        "type": "image",
        "src": "test-full/media/culture/9c.jpg",
        "alt": "Εικ. Γ"
      },
      {
        "id": "D",
        "type": "image",
        "src": "test-full/media/culture/9d.jpg",
        "alt": "Εικ. Δ"
      }
    ],
    "options": ["A", "B", "C", "D"],
    "minSelections": 1,
    "maxSelections": 2,
    "correctAnswer": ["B", "C"]
  },
*/
