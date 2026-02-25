// frontend/src/test-full/pages/LanguageQuestion.tsx

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import EssayGradingSummary from "../components/essay-components/EssayGradingSummary"
import EssayQuestion from "../components/essay-components/EssayQuestion"
import LanguageGradingSummary from "../components/grading-components/LanguageGradingSummary"
import MatchingQuestionComponent from "../components/question-components/MatchingQuestion"
import MultipleChoiceQuestion from "../components/question-components/MultipleChoiceQuestion"
import ShortTextQuestion from "../components/question-components/ShortTextQuestion"
import TrueFalseNAQuestion from "../components/question-components/TrueFalseNAQuestion"
import { useEssayGrading } from "../hooks/useEssayGrading"
import { useFullGrading } from "../hooks/useFullGrading"
import type {
	FullAnswer,
	FullGradedAnswer,
	FullQuestion,
} from "../types/Full.types"
import type { LanguageFullTestType } from "../types/language.types"

type Props = {
	test: LanguageFullTestType
}

const LanguageQuestion = ({ test }: Props) => {
	const [answers, setAnswers] = useState<Record<string, FullAnswer>>({})
	const [gradedResults, setGradedResults] = useState<FullGradedAnswer[]>([])
	const [score, setScore] = useState<number | null>(null)

	const [essayText, setEssayText] = useState("")
	const textRef = useRef<HTMLDivElement | null>(null)

	const { gradeAll } = useFullGrading()
	const { gradeEssay, essayResult, essayLoading } = useEssayGrading()

	const partA = test.parts.A.questions
	const partB = test.parts.B.questions
	const partC = test.parts.C

	const handleGrade = async () => {
		const fullQuestions: FullQuestion[] = [...partA, ...partB]
		const result = await gradeAll(fullQuestions, answers)

		setGradedResults(result.results)
		setScore(result.score)
	}

	const getGraded = (id: string) => gradedResults.find((r) => r.id === id)

	const formatCorrectAnswer = (graded: FullGradedAnswer) => {
		const ca = graded.correctAnswer as unknown

		if (typeof ca === "string") return ca
		if (Array.isArray(ca)) return ca.join(" / ")
		if (ca && typeof ca === "object") {
			// matching / maps
			try {
				return Object.entries(ca as Record<string, unknown>)
					.map(([k, v]) => `${k} → ${String(v)}`)
					.join(", ")
			} catch {
				return "—"
			}
		}

		return "—"
	}

	// highlight logic
	useEffect(() => {
		const element = textRef.current
		if (!element) return

		const highlight = () => {
			const selection = window.getSelection()
			if (!selection || selection.isCollapsed) return

			const range = selection.getRangeAt(0)
			if (!element.contains(range.commonAncestorContainer)) return

			try {
				const span = document.createElement("span")
				span.className = "bg-yellow-300 px-1"
				range.surroundContents(span)
				selection.removeAllRanges()
			} catch {
				selection.removeAllRanges()
			}
		}

		element.addEventListener("mouseup", highlight)
		element.addEventListener("touchend", highlight)

		return () => {
			element.removeEventListener("mouseup", highlight)
			element.removeEventListener("touchend", highlight)
		}
	}, [])

	if (test.active === false) {
		return (
			<div className="max-w-3xl mx-auto py-10">
				<Card>
					<CardHeader>
						<CardTitle>Ανενεργό Τεστ</CardTitle>
					</CardHeader>
					<CardContent className="text-sm text-muted-foreground">
						Αυτό το τεστ είναι ανενεργό (active: false).
					</CardContent>
				</Card>
			</div>
		)
	}

	let index = 1

	return (
		<div className="space-y-10 max-w-5xl mx-auto py-8">
			<Card>
				<CardHeader>
					<CardTitle>{test.title}</CardTitle>
				</CardHeader>
				<CardContent className="space-y-3">
					<p className="font-bold">{test.prompt}</p>
					<div
						ref={textRef}
						className="whitespace-pre-line text-justify leading-5 select-text"
					>
						{test.text}
					</div>
				</CardContent>
			</Card>

			{/* PART A */}
			<div className="space-y-6">
				<h2 className="text-xl font-bold">Μέρος Α</h2>

				{partA.map((q) => {
					const graded = getGraded(q.id)
					const gradedClass =
						gradedResults.length > 0 && graded
							? graded.correct
								? "bg-green-50 border border-green-400"
								: "bg-red-50 border border-red-400"
							: ""

					return (
						<div key={q.id} className="flex items-start gap-2">
							<span className="font-semibold">{index++}.</span>

							<div className={`flex-1 p-4 rounded ${gradedClass}`}>
								{q.type === "multipleChoice" && (
									<MultipleChoiceQuestion
										question={q}
										value={
											typeof answers[q.id] === "string"
												? (answers[q.id] as string)
												: ""
										}
										onChange={(v) =>
											setAnswers((prev) => ({ ...prev, [q.id]: v }))
										}
									/>
								)}

								{q.type === "trueFalseNA" && (
									<TrueFalseNAQuestion
										question={q}
										value={
											typeof answers[q.id] === "string"
												? (answers[q.id] as string)
												: ""
										}
										onChange={(v) =>
											setAnswers((prev) => ({ ...prev, [q.id]: v }))
										}
									/>
								)}

								{gradedResults.length > 0 && graded && !graded.correct && (
									<div className="mt-2 text-sm text-muted-foreground">
										Σωστή απάντηση: {formatCorrectAnswer(graded)}
									</div>
								)}
							</div>
						</div>
					)
				})}
			</div>

			{/* PART B */}
			<div className="space-y-6">
				<h2 className="text-xl font-bold">Μέρος Β</h2>

				{test.parts.B.instructionsMultipleChoice && (
					<p className="text-muted-foreground whitespace-pre-line">
						multiple choice οδηγίες: {test.parts.B.instructionsMultipleChoice}
					</p>
				)}
				{test.parts.B.instructionsShortText && (
					<p className="text-muted-foreground whitespace-pre-line">
						Ερωτήσεις σύντομου κειμένου οδηγίες:{" "}
						{test.parts.B.instructionsShortText}
					</p>
				)}

				{partB.map((q) => {
					const graded = getGraded(q.id)
					const gradedClass =
						gradedResults.length > 0 && graded
							? graded.correct
								? "bg-green-50 border border-green-400"
								: "bg-red-50 border border-red-400"
							: ""

					return (
						<div key={q.id} className="flex items-start gap-2">
							<span className="font-semibold">{index++}.</span>

							<div className={`flex-1 p-4 rounded ${gradedClass}`}>
								{q.type === "multipleChoice" && (
									<MultipleChoiceQuestion
										question={q}
										value={
											typeof answers[q.id] === "string"
												? (answers[q.id] as string)
												: ""
										}
										onChange={(v) =>
											setAnswers((prev) => ({ ...prev, [q.id]: v }))
										}
									/>
								)}

								{q.type === "shortText" && (
									<ShortTextQuestion
										question={q}
										value={answers[q.id]}
										onChange={(v) =>
											setAnswers((prev) => ({ ...prev, [q.id]: v }))
										}
									/>
								)}

								{q.type === "matching" && (
									<MatchingQuestionComponent
										question={q}
										value={
											answers[q.id] &&
											typeof answers[q.id] === "object" &&
											!Array.isArray(answers[q.id])
												? (answers[q.id] as Record<string, string>)
												: {}
										}
										onChange={(v) =>
											setAnswers((prev) => ({ ...prev, [q.id]: v }))
										}
									/>
								)}

								{gradedResults.length > 0 && graded && !graded.correct && (
									<div className="mt-2 text-sm text-muted-foreground">
										Σωστή απάντηση: {formatCorrectAnswer(graded)}
									</div>
								)}
							</div>
						</div>
					)
				})}
			</div>

			{/* PART C */}
			<div>
				<EssayQuestion
					instructions={partC.instructions}
					question={partC.question}
					minWords={partC.minWords}
					maxWords={partC.maxWords}
					value={essayText}
					onChange={setEssayText}
				/>

				<Button
					onClick={() =>
						gradeEssay({
							prompt: partC.question,
							studentText: essayText,
						})
					}
					disabled={essayLoading}
				>
					{essayLoading ? "Αξιολόγηση..." : "Αξιολόγηση Έκθεσης"}
				</Button>
			</div>

			{essayResult && <EssayGradingSummary result={essayResult} />}

			<Button onClick={handleGrade}>Αξιολόγηση.</Button>

			{score !== null && <div className="text-lg font-bold">Σκορ: {score}</div>}

			{gradedResults.length > 0 && (
				<LanguageGradingSummary gradedAnswers={gradedResults} />
			)}
		</div>
	)
}

export default LanguageQuestion
