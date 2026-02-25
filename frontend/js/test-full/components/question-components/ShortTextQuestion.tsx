import { Input } from "@/components/ui/input"
import type { FullAnswer } from "../../types/Full.types"

// value schema: Αν multipleBlanks = false: "Καποδίστριας" Αν multipleBlanks = true: ["Φίλιππος Β΄", "Κωνσταντίνος ΙΑ΄ Παλαιολόγος", ...]
type Props = {
	question: {
		id: string
		prompt?: string
		question: string
		multipleBlanks?: boolean
	}
	value?: FullAnswer
	onChange: (value: FullAnswer) => void
}

const ShortTextQuestion = ({ question, value, onChange }: Props) => {
	// Χωρίζουμε το κείμενο στα "__" placeholders
	const parts = question.question.split("__")
	const blanksCount = parts.length - 1

	// Ελέγχουμε αν το value είναι string[]
	// Type guard για να ξεχωρίζουμε string[] από string
	const isStringArray = (val: unknown): val is string[] => {
		return Array.isArray(val) && val.every((item) => typeof item === "string")
	}

	// Single blank case
	const handleSingleChange = (val: string) => {
		onChange(val)
	}

	// Multiple blanks case
	const handleMultiChange = (index: number, val: string) => {
		const current = isStringArray(value) ? value : []

		const updated = [...current]
		updated[index] = val

		onChange(updated)
	}

	const renderWithBlanks = () => {
		// Αν δεν υπάρχουν "__" → απλό κείμενο
		if (blanksCount === 0) {
			return question.question
		}

		return parts.map((part, index) => (
			<span key={`${part}-${part.length}`}>
				{part}

				{index < blanksCount && (
					<Input
						value={
							question.multipleBlanks
								? isStringArray(value)
									? (value[index] ?? "")
									: ""
								: typeof value === "string"
									? value
									: ""
						}
						onChange={(e) =>
							question.multipleBlanks
								? handleMultiChange(index, e.target.value)
								: handleSingleChange(e.target.value)
						}
						className="
              inline-block
              w-40
              mx-2
              border-0
              border-b-2
              border-black
              rounded-none
              px-1
              focus-visible:ring-0
              focus-visible:ring-offset-0
              focus-visible:border-black
              bg-transparent
              font-semibold
            "
					/>
				)}
			</span>
		))
	}

	return (
		<div className="space-y-2">
			{/* Προαιρετικό prompt (π.χ. οδηγίες) */}
			{question.prompt && (
				<p className="text-muted-foreground whitespace-pre-line">
					{question.prompt}
				</p>
			)}

			<p className="font-medium leading-6 whitespace-pre-line">
				{renderWithBlanks()}
			</p>
		</div>
	)
}

export default ShortTextQuestion

/*
	{
		"id": "HIST_61",
		"category": "ιστορία",
		"active": true,
		"type": "shortText",
		"multipleBlanks": true,
		"question": "Ο (1) __ ήταν βασιλιάς όταν η Μακεδονία υπέταξε και ένωσε όλες τις υπόλοιπες αρχαιοελληνικές πόλεις-κράτη. Τελευταίος αυτοκράτορας του Βυζαντίου ήταν ο (2) __. Την Ελληνική Επανάσταση (3) __. Πρώτος κυβερνήτης του ελληνικού κράτους ήταν ο (4) __.",
		"correctAnswer": [
			"Φίλιππος Β΄",
			"Κωνσταντίνος ΙΑ΄ Παλαιολόγος",
			"Αλέξανδρος Υψηλάντης",
			"Ιωάννης Καποδίστριας"
		]
	},
*/
