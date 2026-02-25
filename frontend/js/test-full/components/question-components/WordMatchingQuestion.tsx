import type { FullWordMatchingQuestion } from "../../types/Full.types"
import QuestionMediaBlock from "../QuestionMediaBlock"

// value schema: { "1": "του Δία", "2": "του Απόλλωνα" } key = blankKey (αριθμός κενού μέσα στο textTemplate), value = wordBank key (πχ "1A", "2B")
type Props = {
	question: FullWordMatchingQuestion
	value: Record<string, string> | undefined
	onChange: (value: Record<string, string>) => void
}

const WordMatchingQuestion = ({ question, value = {}, onChange }: Props) => {
	const handleSelect = (blankKey: string, selected: string) => {
		onChange({
			...value,
			[blankKey]: selected,
		})
	}

	const renderText = () => {
		// textTemplate περιέχει placeholders μορφής: "1. __", "2. __" κλπ.  Με split κρατάμε και τα delimiters, ώστε να τα αντικαταστήσουμε με <select>.
		const parts = question.textTemplate.split(/(\d+\.\s__)/g)

		return parts.map((part) => {
			// Ελέγχουμε αν το κομμάτι είναι placeholder
			const match = part.match(/^(\d+)\.\s__$/)

			// Αν δεν είναι placeholder → απλό κείμενο
			if (!match) return <span key={part}>{part}</span>

			const blankKey = match[1]

			return (
				<span key={blankKey} className="mx-1">
					<select
						value={value[blankKey] || ""}
						onChange={(e) => handleSelect(blankKey, e.target.value)}
						className="border rounded px-2 py-1"
					>
						<option value="">--</option>
						{Object.entries(question.wordBank).map(([k, label]) => (
							<option key={k} value={k}>
								{k}. {label}
							</option>
						))}
					</select>
				</span>
			)
		})
	}

	return (
		<div className="space-y-4">
			<p className="font-medium">{question.question}</p>

			{/* ενας renderer μιας η περισσοτερων εικονων. είναι έτσι σε πολλα components που είναι πιθανό να έχουν πεδία question.media */}
			{question.media && question.media.length > 0 && (
				<QuestionMediaBlock media={question.media} />
			)}

			<div className="leading-8">{renderText()}</div>
		</div>
	)
}

export default WordMatchingQuestion

/*
	{
		"id": "CULT_17",
		"category": "πολιτισμός",
		"active": true,
		"type": "wordMatching",
		"question": "Συμπληρώστε το κενό που υπάρχει σε κάθε πρόταση επιλέγοντας από τις παρακάτω λέξεις.",
		"wordBank": {
			"A": "του Δία",
			"B": "του Απόλλωνα",
			"C": "το Νεκρομαντείο",
			"D": "του Άμμωνος Δία"
		},
		"textTemplate": "Το Μαντείο 1. __ στους Δελφούς ήταν ένα από τα πιο φημισμένα της Αρχαιότητος. Όμως το παλαιότερο Μαντείο ήταν 2. __ στη Δωδώνη. Σπουδαίο μαντείο αποτέλεσε και αυτό 3. __ στην Αίγυπτο. Στον Μεσοπόταμο Πρεβέζης ήταν 4. __, όπου επικοινωνούσαν με τις ψυχές των νεκρών.",
		"correctAnswer": {
			"1": "B",
			"2": "A",
			"3": "D",
			"4": "C"
		},
		"hasExtraOption": false
	},
*/
