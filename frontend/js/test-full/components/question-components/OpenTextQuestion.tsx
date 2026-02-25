import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { FullOpenTextQuestion } from "../../types/Full.types"

// value schema: "Το εκλογικό σύστημα είναι..." Απλό string. Το grading (AI) λαμβάνει αυτό το string αυτούσιο.
type Props = {
	question: FullOpenTextQuestion
	value?: string
	onChange: (value: string) => void
}

const OpenTextQuestion = ({ question, value = "", onChange }: Props) => {
	// Υπολογισμός λέξεων:
	// trim → αφαιρούμε κενά αρχής/τέλους
	// split(/\s+/) → διαχωρισμός σε whitespace
	const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0

	// UI-only validation (δεν κόβει input, απλά ενημερώνει)
	const isOverLimit = wordCount > question.maxWords

	return (
		<div className="space-y-2">
			<Label className="font-medium">{question.question}</Label>

			<Textarea
				value={value}
				onChange={(e) => onChange(e.target.value)}
				className={isOverLimit ? "border-red-500" : ""}
				rows={6}
			/>

			{/* UI feedback — δεν επιβάλλει hard stop */}
			<div className="text-sm text-muted-foreground">
				Λέξεις: {wordCount} / {question.maxWords}
			</div>

			{isOverLimit && (
				<div className="text-sm text-red-500">
					Έχετε υπερβεί το όριο λέξεων.
				</div>
			)}
		</div>
	)
}

export default OpenTextQuestion

/*
	{
		"id": "INST_68",
		"category": "θεσμοί",
		"active": true,
		"type": "openText",
		"question": "Τι είναι «το εκλογικό σύστημα;» Απάντηση: μέχρι πενήντα(50) λέξεις",
		"maxWords": 50,
		"correctAnswer": "Εκλογικό σύστημα είναι ο τρόπος κατανομής των βουλευτικών εδρών και εκλογής των υποψηφίων στις εκλογές. Ορίζεται με ειδικό νόμο ή κανονισμό, ο οποίος ονομάζεται εκλογικός. Με βάση τις διατάξεις του για την εκπροσώπηση των πολιτικών συνδυασμών, διακρίνεται σε τρεις βασικές κατηγορίες: πλειοψηφικό, αναλογικό και σύνθετο ή μικτό."
	},
*/
