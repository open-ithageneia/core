import { router } from "@inertiajs/react"
import { useCallback, useMemo, useRef, useState } from "react"
import { QuizRenderer } from "@/components/quiz/QuizRenderer"
import { Button } from "@/components/ui/button"
import { MultiSelect } from "@/components/ui/multi-select"
import { getScoreColor } from "@/lib/score-color"
import { QUIZ_CATEGORY_LABELS, type QuizCategory } from "@/types/enums"
import type { ExamSession, TrainingData } from "@/types/models"

type CategoryOption = {
	value: string
	label: string
}

type TrainingProps = {
	categories: CategoryOption[]
	exam_sessions: ExamSession[]
	data: TrainingData | null
}

function TrainingSetup({
	categories,
	exam_sessions,
}: {
	categories: CategoryOption[]
	exam_sessions: ExamSession[]
}) {
	const [categories_selected, setCategoriesSelected] = useState<string[]>([])
	const [amount, setAmount] = useState("10")
	const [examSession, setExamSession] = useState("")
	const [quizType, setQuizType] = useState("")

	function handleStart() {
		const params: Record<string, string> = { amount }
		if (categories_selected.length > 0)
			params.category = categories_selected.join(",")
		if (examSession) params.exam_session = examSession
		if (quizType) params.quiz_type = quizType
		router.get("/quiz/training", params, { preserveState: false })
	}

	return (
		<section className="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-sm sm:p-8">
			<h1 className="mb-6 text-2xl font-bold">Τεστ προσομοίωσης</h1>

			<div className="mb-4">
				<label
					htmlFor="exam-session"
					className="mb-1 block text-sm font-medium text-gray-700"
				>
					Εξεταστική περίοδος
				</label>
				<select
					id="exam-session"
					value={examSession}
					onChange={(e) => setExamSession(e.target.value)}
					className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
				>
					<option value="">Όλες οι περίοδοι</option>
					{exam_sessions.map((es) => {
						const monthName = new Date(es.year, es.month - 1).toLocaleString(
							"el-GR",
							{ month: "long" },
						)
						return (
							<option key={es.id} value={String(es.id)}>
								{monthName.charAt(0).toUpperCase() + monthName.slice(1)}{" "}
								{es.year}
							</option>
						)
					})}
				</select>
			</div>

			<div className="mb-4">
				<label
					htmlFor="category"
					className="mb-1 block text-sm font-medium text-gray-700"
				>
					Κατηγορία
				</label>
				<MultiSelect
					options={categories.map((c) => ({
						value: c.value,
						label: QUIZ_CATEGORY_LABELS[c.value as QuizCategory] ?? c.label,
					}))}
					selected={categories_selected}
					onChange={setCategoriesSelected}
					placeholder="Όλες οι κατηγορίες"
				/>
			</div>

			<div className="mb-6">
				<label
					htmlFor="quiz-type"
					className="mb-1 block text-sm font-medium text-gray-700"
				>
					Τύπος ερώτησης
				</label>
				<select
					id="quiz-type"
					value={quizType}
					onChange={(e) => setQuizType(e.target.value)}
					className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
				>
					<option value="">Όλοι οι τύποι</option>
					<option value="Statement">Σωστό / Λάθος & Πολλαπλής επιλογής</option>
					<option value="DragAndDrop">Κατάταξη</option>
					<option value="Matching">Αντιστοίχηση</option>
					<option value="FillInTheBlank">Συμπλήρωση κενού</option>
					<option value="OpenEnded">Ανοιχτή ερώτηση</option>
				</select>
			</div>

			<div className="mb-6">
				<label
					htmlFor="amount"
					className="mb-1 block text-sm font-medium text-gray-700"
				>
					Αριθμός ερωτήσεων
				</label>
				<select
					id="amount"
					value={amount}
					onChange={(e) => setAmount(e.target.value)}
					className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
				>
					<option value="5">5</option>
					<option value="10">10</option>
					<option value="20">20</option>
				</select>
			</div>

			<Button onClick={handleStart} className="w-full">
				Ξεκινήστε
			</Button>
		</section>
	)
}

function TrainingSession({ data }: { data: TrainingData }) {
	const [currentIndex, setCurrentIndex] = useState(0)
	const [validatedSet, setValidatedSet] = useState<Set<number>>(new Set())
	const scoresRef = useRef<Map<number, { correct: number; total: number }>>(
		new Map(),
	)
	const [scoreVersion, setScoreVersion] = useState(0)

	const POINTS_PER_QUESTION = 2

	const scoreCallbacks = useMemo(
		() =>
			data.map((_, index) => (correct: number, total: number) => {
				scoresRef.current.set(index, { correct, total })
				setScoreVersion((v) => v + 1)
			}),
		[data],
	)

	const { earnedPoints, maxPoints, earnedUpToCurrent } = useMemo(() => {
		void scoreVersion
		let earned = 0
		let earnedUpto = 0
		const max = data.length * POINTS_PER_QUESTION
		for (const [idx, { correct, total }] of scoresRef.current.entries()) {
			const pts = total > 0 ? (correct / total) * POINTS_PER_QUESTION : 0
			earned += pts
			if (idx <= currentIndex) earnedUpto += pts
		}
		return {
			earnedPoints: Math.round(earned * 100) / 100,
			maxPoints: max,
			earnedUpToCurrent: Math.round(earnedUpto * 100) / 100,
		}
	}, [scoreVersion, data.length, currentIndex])

	const total = data.length
	const isFirst = currentIndex === 0
	const isLast = currentIndex === total - 1
	const isCurrentValidated = validatedSet.has(currentIndex)
	const allValidated = validatedSet.size === total

	const handleValidate = useCallback(() => {
		setValidatedSet((prev) => new Set(prev).add(currentIndex))
	}, [currentIndex])

	const goNext = useCallback(() => {
		if (currentIndex < total - 1) setCurrentIndex((i) => i + 1)
	}, [currentIndex, total])

	const goPrev = useCallback(() => {
		if (currentIndex > 0) setCurrentIndex((i) => i - 1)
	}, [currentIndex])

	if (total === 0) {
		return (
			<section className="mx-auto max-w-md rounded-2xl bg-white p-6 text-center shadow-sm">
				<h1 className="mb-4 text-xl font-bold">Δεν βρέθηκαν ερωτήσεις</h1>
				<p className="mb-4 text-sm text-gray-600">
					Δοκιμάστε διαφορετική κατηγορία ή αριθμό ερωτήσεων.
				</p>
				<Button onClick={() => router.get("/quiz/training")}>
					Πίσω στις ρυθμίσεις
				</Button>
			</section>
		)
	}

	return (
		<section className={`flex ${allValidated ? "" : "h-full"} flex-col`}>
			{allValidated && (
				<div className="sticky top-0 z-10 rounded-2xl bg-white p-2 text-center shadow-sm">
					<h1 className="mb-1 text-2xl font-bold">Αποτελέσματα</h1>
					<p className="mb-1 text-3xl font-bold text-blue-600">
						{earnedPoints} / {maxPoints}
					</p>
					<p className="mb-2 text-sm text-gray-600">
						Δείτε τις σωστές και λάθος απαντήσεις σας παρακάτω.
					</p>
					<Button
						variant="outline"
						onClick={() => router.get("/quiz/training")}
					>
						Νέο τεστ
					</Button>
				</div>
			)}

			{!allValidated && (
				<div className="shrink-0 rounded-2xl bg-white p-4 shadow-sm">
					<div className="mb-2 flex items-center justify-between text-sm text-gray-600">
						<span>
							Ερώτηση {currentIndex + 1} από {total}
						</span>
						<span className="text-sm font-medium text-blue-600">
							Βαθμολογία: {earnedUpToCurrent} /{" "}
							{(currentIndex + 1) * POINTS_PER_QUESTION}
						</span>
					</div>
					<div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
						<div
							className="h-full rounded-full bg-blue-500 transition-all duration-300"
							style={{
								width: `${((currentIndex + 1) / total) * 100}%`,
							}}
						/>
					</div>
				</div>
			)}

			<div className={`${allValidated ? "space-y-4" : "min-h-0 flex-1"} py-1`}>
				{data.map((item, idx) => {
					const score = scoresRef.current.get(idx)
					const earned =
						score && score.total > 0
							? Math.round(
									(score.correct / score.total) * POINTS_PER_QUESTION * 100,
								) / 100
							: 0
					const ratio = earned / POINTS_PER_QUESTION
					return (
						<div
							key={`${item.quiz_type}-${item.id}`}
							className={
								!allValidated && idx !== currentIndex
									? "hidden"
									: !allValidated
										? "h-full"
										: ""
							}
						>
							<QuizRenderer
								item={item}
								index={idx + 1}
								forceValidation={validatedSet.has(idx)}
								onScore={scoreCallbacks[idx]}
								badge={
									allValidated && score ? (
										<span
											className="text-sm font-bold"
											style={{ color: getScoreColor(ratio) }}
										>
											{earned} / {POINTS_PER_QUESTION}
										</span>
									) : undefined
								}
							/>
						</div>
					)
				})}
			</div>

			{!allValidated && (
				<div className="sticky bottom-0 flex shrink-0 items-center justify-between rounded-2xl bg-white p-4 shadow-sm">
					<Button variant="outline" onClick={goPrev} disabled={isFirst}>
						← Προηγούμενη
					</Button>

					{!isCurrentValidated ? (
						<Button onClick={handleValidate}>Έλεγχος</Button>
					) : isLast ? (
						<span className="text-sm text-gray-500">✓ Ελεγμένη</span>
					) : (
						<Button onClick={goNext}>Επόμενη →</Button>
					)}
				</div>
			)}
		</section>
	)
}

export default function Training({
	categories,
	exam_sessions,
	data,
}: TrainingProps) {
	if (!data) {
		return (
			<TrainingSetup categories={categories} exam_sessions={exam_sessions} />
		)
	}
	return <TrainingSession data={data} />
}
