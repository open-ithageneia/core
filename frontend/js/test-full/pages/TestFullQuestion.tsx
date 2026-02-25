// frontend\src\test-full\pages\TestFullQuestion.tsx

// Central dispatcher component: επιλέγει renderer ανά type
/*
1. shortText → πχ μια ή λίγες λέξεις
2. matching → ερωτήσεις αντιστοίχησης
3. multiSelect → multiple με περισσοτερες της μια σωστές απαντήσεις
4. listInput → ελευθερο κείμενο λίγων λέξεων σαν «Σημείωσε 5 χώρες της ΕΕ»
5. trueFalseGroup → μπλοκ ερωτήσεων σωστο/λαθος. Η απλή σωστο/λαθος ειναι multiple
6. mapPoints → βάλε σημείο σε χάρτη
7. categorization → χώρισε τα αντικείμενα σε δύο λίστες ("ποιες απο τις παρακάτω πόλεις ανηκουν στην νησιωτική ή ηπειρωτική ελλάδα")
8. wordMatching → Συμπλήρωση κενών μέσα σε κείμενο από word bank.
9. openText → ερωτήσεις σύντομης έκθεσης. πάνε σε openAI
10. τα ήδη των ερωτήσεων που διαχειρίζεται αυτή τη στιγμή είναι:
multipleChoice → α,β,γ,δ
*/

import MapPointsGradingBlock from "../components/map-components/MapPointsGradingBlock"
import MapPointsQuestion from "../components/map-components/MapPointsQuestion"
import CategorizationQuestionComponent from "../components/question-components/CategorizationQuestionComponent"
import ListInputQuestion from "../components/question-components/ListInputQuestion"
import MatchingQuestionComponent from "../components/question-components/MatchingQuestion"
import MultipleChoiceQuestion from "../components/question-components/MultipleChoiceQuestion"
import MultiSelectQuestion from "../components/question-components/MultiSelectQuestion"
import OpenTextQuestion from "../components/question-components/OpenTextQuestion"
import ShortTextQuestion from "../components/question-components/ShortTextQuestion"
import TrueFalseGroupQuestion from "../components/question-components/TrueFalseGroupQuestion"
import WordMatchingQuestion from "../components/question-components/WordMatchingQuestion"
import type {
	FullAnswer,
	FullGradedAnswer,
	FullQuestion,
	MapPoint,
} from "../types/Full.types"

type Props = {
	question: FullQuestion // Το πλήρες αντικείμενο της ερώτησης (type, prompt, options κλπ).
	value?: FullAnswer // Η απάντηση του χρήστη
	onChange: (id: string, value: FullAnswer) => void
	// ο λόγος που τα στέλνει αυτα είναι γιατί κάθε ερώτηση μετα την αξιολογηση φαίνεται πράσινη/κόκκινη και δείχνει την προτεινόμενη απάντηση
	gradedAnswer?: FullGradedAnswer //Το αποτέλεσμα βαθμολόγησης για τη συγκεκριμένη ερώτηση
	showGrading?: boolean // Αν πρέπει να εμφανιστεί feedback/σωστή απάντηση
}

// έχουμε πολλών διαφορετικών τύπων ερωτήσεις που επιστρέφουν answer με διαφορετικές μορφές και schema. Αυτή η helper func μου τα κάνει σε string
// πχ ["A", "B"] → "A, B", { A: "1", B: "2" } → "A: 1 | B: 2", { group1: ["A","B"] } → "group1: A, B"
// χρησιμοποιείται μόνο για feedback UI
const formatCorrectAnswer = (answer: unknown): string => {
	if (!answer) return ""

	if (Array.isArray(answer)) {
		return answer.join(", ")
	}

	if (typeof answer === "object") {
		return Object.entries(answer)
			.map(([key, value]) =>
				Array.isArray(value)
					? `${key}: ${value.join(", ")}`
					: `${key}: ${String(value)}`,
			)
			.join(" | ")
	}

	return String(answer)
}

const GeographyFullQuestion = ({
	question,
	value,
	onChange,
	gradedAnswer,
	showGrading,
}: Props) => {
	// ενα μικρό component για την εμφάνιση του αποτελέσματος της κάθε ερώτησης
	// εμφανίζει την σωστή απάντηση μόνο αν ο user είχε βάλει λάθος
	// οι ερωτήσεις χάρτη λόγο ιδιαιτερότητας εξαιρούνται και διαχειρίζονται χωριστά
	const correctAnswerBlock =
		showGrading &&
		gradedAnswer &&
		!gradedAnswer.correct &&
		question.type !== "mapPoints" ? (
			<div className="mt-3 p-3 bg-muted rounded text-sm">
				<p className="font-semibold">Σωστή απάντηση:</p>
				<p>{formatCorrectAnswer(gradedAnswer.correctAnswer)}</p>
			</div>
		) : null

	// απλως τα styling classnames που μου κάνουν το κουτί πρασινο/κόκκινο μετά την αξιολογηση για να μην επαναλαμβάνονται κάθε φορα
	const gradedClass =
		showGrading && gradedAnswer
			? gradedAnswer.correct
				? "bg-green-50 border border-green-400"
				: "bg-red-50 border border-red-400"
			: ""

	return (
		// εδω καθε φορά έρχεται μια ερώτηση με ένα switch like στιλ αυτή κατευθύνετε στον αντιστοιχο renderer component. κάθε φορα περνάμε την πλήρη json ερωτηση και το state της απάντησης που βρίσκετε στην pagePicker

		// σε πολλά το value(απαντήσεις μαθητή) έχει ts narrowing για να μην περνάει κάτι άλλο εκτος απο array απαντήσεων

		<div className={`space-y-4 border p-4 rounded ${gradedClass}`}>
			{/* radio btn */}
			{question.type === "multipleChoice" && (
				<MultipleChoiceQuestion
					question={question}
					value={value as string}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{/* checkbox */}
			{question.type === "multiSelect" && (
				<MultiSelectQuestion
					question={question}
					value={
						question.type === "multiSelect" && Array.isArray(value)
							? (value as string[])
							: []
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{/* select (html)*/}
			{question.type === "matching" && (
				<MatchingQuestionComponent
					question={question}
					value={
						value && typeof value === "object" && !Array.isArray(value)
							? value
							: {}
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{/* Input */}
			{question.type === "listInput" && (
				<ListInputQuestion
					question={question}
					value={
						question.type === "listInput" && Array.isArray(value)
							? (value as string[])
							: []
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{/* radio */}
			{question.type === "trueFalseGroup" && (
				<TrueFalseGroupQuestion
					question={question}
					value={
						value && typeof value === "object" && !Array.isArray(value)
							? (value as Record<string, "T" | "F">)
							: {}
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{/* Select (shadCN)*/}
			{question.type === "categorization" && (
				<CategorizationQuestionComponent
					question={question}
					value={
						value && typeof value === "object" && !Array.isArray(value)
							? value
							: {}
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{/* input */}
			{question.type === "shortText" && (
				<ShortTextQuestion
					question={question}
					value={value}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{/* select */}
			{question.type === "wordMatching" && (
				<WordMatchingQuestion
					question={question}
					value={
						value && typeof value === "object" && !Array.isArray(value)
							? (value as Record<string, string>)
							: {}
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{/* Textarea */}
			{question.type === "openText" && (
				<OpenTextQuestion
					question={question}
					value={typeof value === "string" ? value : ""}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "mapPoints" && (
				<>
					<MapPointsQuestion
						question={question}
						value={
							question.type === "mapPoints"
								? (value as MapPoint[] | undefined)
								: undefined
						}
						onChange={(val) => onChange(question.id, val)}
					/>

					{showGrading &&
						gradedAnswer &&
						gradedAnswer.mapReviewPoints &&
						gradedAnswer.mapGradedPoints && (
							<div className="mt-4">
								<MapPointsGradingBlock
									reviewPoints={gradedAnswer.mapReviewPoints}
									gradedPoints={gradedAnswer.mapGradedPoints}
								/>
							</div>
						)}
				</>
			)}

			{correctAnswerBlock}
		</div>
	)
}

export default GeographyFullQuestion
