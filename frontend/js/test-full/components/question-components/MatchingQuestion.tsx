// frontend\src\test-full\components\MatchingQuestion.tsx

import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table"
import type { FullMatchingQuestion } from "../../types/Full.types"
import QuestionMediaBlock from "../QuestionMediaBlock"

// value schema: { "1": "C", "2": "A" } όπου key = columnA.key και value = columnB.key
type Props = {
	question: FullMatchingQuestion
	value?: Record<string, string>
	onChange: (value: Record<string, string>) => void
}

const MatchingQuestionComponent = ({
	question,
	value = {},
	onChange,
}: Props) => {
	// χρειάζεται νέο γιατι ο Parent δεν ξέρει το schema κάθε ερώτησης
	const handleSelect = (rowKey: string, selected: string) => {
		onChange({
			...value,
			[rowKey]: selected,
		})
	}

	return (
		<div className="space-y-6">
			{/* Εκφώνηση */}
			<p className="font-medium">{question.question}</p>

			{/* ενας renderer μιας η περισσοτερων εικονων. είναι έτσι σε πολλα components που είναι πιθανό να έχουν πεδία question.media */}
			{question.media && question.media.length > 0 && (
				<QuestionMediaBlock media={question.media} />
			)}

			{/* ===== ΣΤΑΤΙΚΟΣ ΠΙΝΑΚΑΣ ΕΚΦΩΝΗΣΗΣ ===== */}
			<Table className="w-full border border-black text-center">
				<TableHeader>
					<TableRow className="border-b border-black">
						<TableHead className="w-1/2 font-bold border-r border-black">
							Στήλη Ι
							<div className="font-semibold">{question.columnAHeader}</div>
						</TableHead>

						<TableHead className="w-1/2 font-bold">
							Στήλη ΙΙ
							<div className="font-semibold">{question.columnBHeader}</div>
						</TableHead>
					</TableRow>
				</TableHeader>

				<TableBody>
					{question.columnA.map((item, index) => (
						<TableRow key={item.key} className="border-b border-black">
							<TableCell className="border-r border-black font-semibold">
								{item.key}. {item.label}
							</TableCell>

							<TableCell className="font-semibold">
								{question.columnB[index]
									? `${question.columnB[index].key}. ${question.columnB[index].label}`
									: ""}
							</TableCell>
						</TableRow>
					))}
				</TableBody>
			</Table>

			{/* ===== INTERACTIVE MATCHING ===== */}
			<div>
				<p className="mb-2 font-semibold">Επιλέξτε την σωστή αντιστοίχιση:</p>

				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>Στήλη Ι</TableHead>
							<TableHead>Αντιστοίχιση</TableHead>
						</TableRow>
					</TableHeader>

					<TableBody>
						{question.columnA.map((item) => (
							<TableRow key={item.key}>
								<TableCell>
									{item.key}. {item.label}
								</TableCell>

								<TableCell>
									{/* χρησιμοποιούμε select γιατι είχαμε προβλήματα σε mobile Opera browser */}
									<select
										className="w-52 rounded-md border border-input bg-background px-3 py-2 text-sm"
										value={value[item.key] ?? ""}
										onChange={(e) => handleSelect(item.key, e.target.value)}
									>
										<option value="">Επιλογή</option>

										{question.columnB.map((opt) => (
											<option key={opt.key} value={opt.key}>
												{opt.key}. {opt.label}
											</option>
										))}
									</select>
								</TableCell>
							</TableRow>
						))}
					</TableBody>
				</Table>
			</div>
		</div>
	)
}

export default MatchingQuestionComponent

/*
	{
		"id": "CULT_16",
		"category": "πολιτισμός",
		"active": true,
		"type": "matching",
		"question": "Να αναγνωρίσετε τα μνημεία που απεικονίζονται στις φωτογραφίες.",
		"media": [
			{
				"id": "A",
				"type": "image",
				"src": "test-full/media/culture/16a.jpg",
				"alt": "Εικ. Α"
			},
			{
				"id": "B",
				"type": "image",
				"src": "test-full/media/culture/16b.jpg",
				"alt": "Εικ. Β"
			},
			{
				"id": "C",
				"type": "image",
				"src": "test-full/media/culture/16c.jpg",
				"alt": "Εικ. Γ"
			},
			{
				"id": "D",
				"type": "image",
				"src": "test-full/media/culture/16d.jpg",
				"alt": "Εικ. Δ"
			}
		],
		"columnAHeader": "Μνημεία",
		"columnBHeader": "Εικόνες",
		"columnA": [
			{ "key": "1", "label": "Οι στύλοι του Ολυμπίου Διός στην Αθήνα" },
			{ "key": "2", "label": "Η Θόλος των Δελφών" },
			{ "key": "3", "label": "Η Πύλη των Λεόντων στις Μυκήνες" },
			{ "key": "4", "label": "Ο Ναός Ποσειδώνος στο Σούνιο" }
		],
		"columnB": [
			{ "key": "A", "label": "Εικ. Α" },
			{ "key": "B", "label": "Εικ. Β" },
			{ "key": "C", "label": "Εικ. Γ" },
			{ "key": "D", "label": "Εικ. Δ" }
		],
		"correctAnswer": {
			"1": "C",
			"2": "B",
			"3": "D",
			"4": "A"
		}
	},
*/
