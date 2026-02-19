import MultipleChoiceQuestion from "../components/MultipleChoiceQuestion"
import TrueFalseGroupQuestion from "../components/TrueFalseGroupQuestion"
import type {
	FullAnswer,
	FullGradedAnswer,
	FullQuestion,
} from "../types/Full.types"

type Props = {
	question: FullQuestion
	value?: FullAnswer
	onChange: (id: string, value: FullAnswer) => void
	gradedAnswer?: FullGradedAnswer
	showGrading?: boolean
}

const formatCorrectAnswer = (answer: unknown): string => {
	if (!answer) return ""

	if (typeof answer === "object") {
		return Object.entries(answer)
			.map(([key, value]) => `${key}: ${String(value)}`)
			.join(" | ")
	}

	return String(answer)
}

const AudioQuestion = ({
	question,
	value,
	onChange,
	gradedAnswer,
	showGrading,
}: Props) => {
	const gradedClass =
		showGrading && gradedAnswer
			? gradedAnswer.correct
				? "bg-green-50 border border-green-400"
				: "bg-red-50 border border-red-400"
			: ""

	const correctAnswerBlock =
		showGrading && gradedAnswer && !gradedAnswer.correct ? (
			<div className="mt-3 p-3 bg-muted rounded text-sm">
				<p className="font-semibold">Σωστή απάντηση:</p>
				<p>{formatCorrectAnswer(gradedAnswer.correctAnswer)}</p>
			</div>
		) : null

	return (
		<div className={`space-y-4 border p-4 rounded ${gradedClass}`}>
			{question.type === "multipleChoice" && (
				<MultipleChoiceQuestion
					question={question}
					value={value as string}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

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

			{correctAnswerBlock}
		</div>
	)
}

export default AudioQuestion
