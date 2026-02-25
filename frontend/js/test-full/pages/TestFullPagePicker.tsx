// frontend\src\test-full\pages\TestFullPagePicker.tsx

/*
1. καλεί το hook της αξιολογησης
2. φέρνει data απο JSON
3. κάνει shuffle τους πινακες και παίρνει τις Ν πρώτες ερωτήσεις απο το καθένα
4. κάνει render τις ερωτήσεις στην σωστή σειρά καλωντας το TestFullQuestion για κάθε μια ερώτηση
5. με την handleChange αποθηκεύει στο state την απάντηση, φτιάχνει έναν ενιαίο πίνακα απαντήσεων και τον στέλνει για βαθμολόγηση στην useFullGrading
6. αν έχουμε αποτελέσματα τα προβάλει με την FullGradingSummary
*/
import { useState } from "react"
import { Button } from "@/components/ui/button"
import FullGradingSummary from "../components/grading-components/FullGradingSummary"
import cultureData from "../data/cultureData.json"
import geoData from "../data/geoData.json"
import historyData from "../data/historyData.json"
import instiData from "../data/instiData.json"
import { useFullGrading } from "../hooks/useFullGrading"
import type {
	FullAnswer,
	FullGradedAnswer,
	FullQuestion,
} from "../types/Full.types"
import TestFullQuestion from "./TestFullQuestion"

type QuestionGroups = {
	geography: FullQuestion[]
	culture: FullQuestion[]
	history: FullQuestion[]
	institutions: FullQuestion[]
}

type Props = {
	// πόσες ερωτήσεις θα εμφανιστούν
	geoCount?: number
	cultCount?: number
	histCount?: number
	instCount?: number
}

const GeographyFullPagePicker = ({
	geoCount = 4,
	cultCount = 4,
	histCount = 6,
	instCount = 6,
}: Props) => {
	const [selectedQuestions, setSelectedQuestions] = useState<QuestionGroups>({
		geography: [],
		culture: [],
		history: [],
		institutions: [],
	})
	const [answers, setAnswers] = useState<Record<string, FullAnswer>>({})
	const [gradedAnswers, setGradedAnswers] = useState<FullGradedAnswer[]>([])
	const [_score, setScore] = useState<number | null>(null)
	const [enableOpenText, setEnableOpenText] = useState(true)

	// φέρνουμε τα data απο τα json
	const geoQuestions = geoData as FullQuestion[]
	const cultureQuestions = cultureData as FullQuestion[]
	const historyQuestions = historyData as FullQuestion[]
	const instQuestions = instiData as FullQuestion[]

	// φέρνουμε τις εξισωσης αξιολογησης απο το hook
	const { gradeAll } = useFullGrading()

	// για επιλογή χωρίς ερωτήσεις open text
	const availableInst = enableOpenText
		? instQuestions
		: instQuestions.filter((q) => q.type !== "openText")

	// επιλογή τυχαίων ερωτήσεων
	const pickRandomQuestions = () => {
		//αντίγραφο του array (ώστε να μην αλλάξεις το original JSON)
		// τυχαίο ανακάτεμα: η sort συγκρίνει ζευγάρια στοιχείων και επειδή επιστρέφουμε τυχαία θετικό/αρνητικό αριθμό, η σειρά προκύπτει τυχαία
		const shuffledGeo = [...geoQuestions].sort(() => 0.5 - Math.random())

		const shuffledCulture = [...cultureQuestions].sort(
			() => 0.5 - Math.random(),
		)

		const shuffledHistory = [...historyQuestions].sort(
			() => 0.5 - Math.random(),
		)

		const shuffledInst = [...availableInst].sort(() => 0.5 - Math.random())

		setSelectedQuestions({
			geography: shuffledGeo.slice(0, geoCount),
			culture: shuffledCulture.slice(0, cultCount),
			history: shuffledHistory.slice(0, histCount),
			institutions: shuffledInst.slice(0, instCount),
		})

		setAnswers({})
		setGradedAnswers([])
		setScore(null)
	}

	const handleChange = (id: string, value: FullAnswer) => {
		setAnswers((prev) => ({
			...prev,
			[id]: value,
		}))
	}

	// κάνουμε flatten και βάζουμε σε ένα ενιαίο array όλες τις ερωτήσεις για να  μπορούν να βαθμολογηθούν ενιαία
	const allQuestions = [
		...selectedQuestions.geography,
		...selectedQuestions.culture,
		...selectedQuestions.history,
		...selectedQuestions.institutions,
	]

	const hasQuestions =
		selectedQuestions.geography.length > 0 ||
		selectedQuestions.culture.length > 0 ||
		selectedQuestions.history.length > 0 ||
		selectedQuestions.institutions.length > 0

	// η gradeAll απο το hook παίρνει όλες τις ερωτήσεις και τις απαντήσεις του μαθητή και επιστρέφει results και score
	// η results είναι ένα [] απο {} ανα ερώτηση που στείλαμε. πχ:
	//   {
	//   id: "geo_1",
	//   userAnswer: "A",
	//   correctAnswer: "B",
	//   correct: false,
	//   type: "multipleChoice"
	// }
	//  και score απλώς το πλήθος των ερωτήσεων που έχουν correct: true
	const handleGradeAll = async () => {
		const { results, score } = await gradeAll(allQuestions, answers)
		setGradedAnswers(results)
		setScore(score)
	}

	// σκορ ανα θεματική
	const geoTotal = selectedQuestions.geography.length
	const cultTotal = selectedQuestions.culture.length
	const histTotal = selectedQuestions.history.length
	const instTotal = selectedQuestions.institutions.length

	//  για την κάθε θεματική ελέγχει πρώτα αν η κάθε απάντηση είναι μέρος της θεματικής και αν έχει απαντηθεί σωστα. μου επιστρέφει πόσες έχουν απαντηθεί σωστά
	const geoScore = gradedAnswers.filter(
		(a) => selectedQuestions.geography.some((q) => q.id === a.id) && a.correct,
	).length

	const cultScore = gradedAnswers.filter(
		(a) => selectedQuestions.culture.some((q) => q.id === a.id) && a.correct,
	).length

	const histScore = gradedAnswers.filter(
		(a) => selectedQuestions.history.some((q) => q.id === a.id) && a.correct,
	).length

	const instScore = gradedAnswers.filter(
		(a) =>
			selectedQuestions.institutions.some((q) => q.id === a.id) && a.correct,
	).length

	const totalScore = geoScore + cultScore + histScore + instScore
	const totalQuestions = geoTotal + cultTotal + histTotal + instTotal

	// Αυτό είναι μετρητής αρίθμησης ερωτήσεων για το UI.
	let questionIndex = 1

	return (
		<div className="max-w-4xl mx-auto py-10 space-y-8">
			<Button onClick={pickRandomQuestions}>Τυχαίες Ερωτήσεις</Button>

			{/* έχουμε προσθέσει την επιλογή να μην εμφανίζονται ερωτήσεις τύπου open text που κάνουν call στο openAI api κυρίως για dev λόγους αλλα ας μείνει προς το παρόν */}
			<Button
				variant={enableOpenText ? "default" : "secondary"}
				onClick={() => setEnableOpenText((prev) => !prev)}
			>
				{enableOpenText ? "Open Text ON" : "Open Text OFF"}
			</Button>

			{/* ακολουθούν renderer για τον κάθε θεματική ερωτήσεων όπου παίρνουν την κάθε ερώτηση της θεματικής και την στέλνουν στο TestFullQuestion question component που είναι υπεύθυνο για να κάνει render μια μια τις ερωτήσεις ανάλογα με τον τύπο της */}
			{selectedQuestions.geography.length > 0 && (
				<>
					<h2 className="text-xl font-bold">Ερωτήσεις Γεωγραφίας</h2>

					{selectedQuestions.geography.map((q) => (
						<div key={q.id} className="flex items-start gap-2">
							{/* η αριθμηση της ερωτησης. είναι εξωτερικά γιατί θέλουμε να συνεχιζει στην αλλαγή θεματικής */}
							<span className="font-semibold">{questionIndex++}.</span>
							<TestFullQuestion
								key={q.id}
								question={q} // Ολόκληρο το αντικείμενο της ερώτησης (τύπος, prompt, options, σωστές απαντήσεις κλπ)
								value={answers[q.id]} // Η απάντηση του χρήστη για αυτή την ερώτηση (από το state answers)
								onChange={handleChange}
								// ο λόγος που τα στέλνει αυτα είναι γιατί κάθε ερώτηση μετα την αξιολογηση φαίνεται πράσινη/κόκκινη και δείχνει την προτεινόμενη απάντηση
								gradedAnswer={gradedAnswers.find((a) => a.id === q.id)} // Το αποτέλεσμα βαθμολόγησης για τη συγκεκριμένη ερώτηση (αν υπάρχει).
								showGrading={gradedAnswers.length > 0} // Boolean: αν έχει γίνει αξιολόγηση, εμφάνισε feedback.
							/>
						</div>
					))}
				</>
			)}

			{selectedQuestions.culture.length > 0 && (
				<>
					<h2 className="text-xl font-bold mt-8">Ερωτήσεις Πολιτισμού</h2>

					{selectedQuestions.culture.map((q) => (
						<div key={q.id} className="flex items-start gap-2">
							<span className="font-semibold">{questionIndex++}.</span>
							<TestFullQuestion
								key={q.id}
								question={q}
								value={answers[q.id]}
								onChange={handleChange}
								gradedAnswer={gradedAnswers.find((a) => a.id === q.id)}
								showGrading={gradedAnswers.length > 0}
							/>
						</div>
					))}
				</>
			)}

			{selectedQuestions.history.length > 0 && (
				<>
					<h2 className="text-xl font-bold mt-8">Ερωτήσεις Ιστορίας</h2>

					{selectedQuestions.history.map((q) => (
						<div key={q.id} className="flex items-start gap-2">
							<span className="font-semibold">{questionIndex++}.</span>
							<TestFullQuestion
								key={q.id}
								question={q}
								value={answers[q.id]}
								onChange={handleChange}
								gradedAnswer={gradedAnswers.find((a) => a.id === q.id)}
								showGrading={gradedAnswers.length > 0}
							/>
						</div>
					))}
				</>
			)}

			{selectedQuestions.institutions.length > 0 && (
				<>
					<h2 className="text-xl font-bold mt-8">Ερωτήσεις Θεσμών</h2>

					{selectedQuestions.institutions.map((q) => (
						<div key={q.id} className="flex items-start gap-2">
							<span className="font-semibold">{questionIndex++}.</span>
							<TestFullQuestion
								key={q.id}
								question={q}
								value={answers[q.id]}
								onChange={handleChange}
								gradedAnswer={gradedAnswers.find((a) => a.id === q.id)}
								showGrading={gradedAnswers.length > 0}
							/>
						</div>
					))}
				</>
			)}

			{hasQuestions && <Button onClick={handleGradeAll}>Αξιολόγηση</Button>}

			{/* σκορ ανα θεματική */}
			{gradedAnswers.length > 0 && (
				<div className="space-y-2 border p-4 rounded bg-muted/20">
					<p>
						Γεωγραφία: {geoScore} / {geoTotal}
					</p>
					<p>
						Πολιτισμός: {cultScore} / {cultTotal}
					</p>
					<p>
						Ιστορία: {histScore} / {histTotal}
					</p>
					<p>
						Θεσμοί: {instScore} / {instTotal}
					</p>
					<p className="font-bold">
						Σύνολο: {totalScore} / {totalQuestions}
					</p>
				</div>
			)}

			{/* συνολικό σκορ */}
			{gradedAnswers.length > 0 && (
				<FullGradingSummary gradedAnswers={gradedAnswers} />
			)}
		</div>
	)
}

export default GeographyFullPagePicker
