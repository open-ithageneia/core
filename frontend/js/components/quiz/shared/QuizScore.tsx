import { useQuizResults } from "./QuizResultsContext"

const POINTS_PER_QUESTION = 2

type QuizScoreProps = {
	correctAnswersCount: number
	totalSubAnswers: number
	showValidation: boolean
}

export default function QuizScore({
	correctAnswersCount,
	totalSubAnswers,
	showValidation,
}: QuizScoreProps) {
	const { hideScore } = useQuizResults()
	if (hideScore) return null
	if (!showValidation || totalSubAnswers === 0) return null

	const earned =
		Math.round(
			(correctAnswersCount / totalSubAnswers) * POINTS_PER_QUESTION * 100,
		) / 100

	return (
		<p className="mt-3 text-center text-sm font-medium text-muted-foreground">
			Βαθμολογία: {earned} / {POINTS_PER_QUESTION}
		</p>
	)
}
