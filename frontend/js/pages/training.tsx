import { router } from "@inertiajs/react"
import { useCallback, useMemo, useRef, useState } from "react"
import { ExitConfirmDialog } from "@/components/exit-confirm-dialog"
import { QuizRenderer } from "@/components/quiz/quiz-renderer"
import { ResultsBanner } from "@/components/quiz/shared/results-banner"
import { Button } from "@/components/ui/button"
import { MultiSelect } from "@/components/ui/multi-select"
import { useExitConfirmation } from "@/hooks/use-exit-confirmation"
import { getScoreColor } from "@/lib/score-color"
import {
	QUIZ_CATEGORY_LABELS,
	QuizCategory,
	StatementType,
} from "@/types/enums"
import type { QuizData, QuizDataItem, StatementModel } from "@/types/models"

type CategoryOption = {
	value: string
	label: string
}

// Knowledge questions are worth a flat 2 points each, shared proportionally
// between their sub-answers.
const POINTS_PER_QUESTION = 2
// A listening question is scored per sub-answer instead — 1.5 points each, the
// same as the listening simulation (e.g. 5 true/false + 5 multiple choice → 15).
const POINTS_PER_SUB_ANSWER = 1.5

type Score = { correct: number; total: number }

function round2(value: number): number {
	return Math.round(value * 100) / 100
}

/**
 * How many sub-answers a statement is scored on — the `total` it reports
 * through `onScore`. A true/false block is a list of statements each marked
 * σωστό/λάθος on its own, so it is worth as many sub-answers as it has choices;
 * a multiple-choice question is one all-or-nothing unit however many options it
 * offers. Mirrors `useTrueFalse` and `useMultipleChoice`.
 */
function statementSubAnswers(statement: StatementModel): number {
	return statement.type === StatementType.TRUE_FALSE
		? statement.content.choices.length
		: 1
}

/**
 * Points earned and available for a single question. A listening question's
 * maximum comes from the sub-answers it asks, so unlike a knowledge question it
 * is not a fixed number — it is counted off the question itself rather than
 * taken from the reported score, which stays 0 until the question is checked.
 */
function questionPoints(
	item: QuizDataItem,
	score: Score | undefined,
): { earned: number; max: number } {
	if (item.quiz_type === "Listening") {
		const subAnswers = item.parts.reduce(
			(sum, part) =>
				sum + part.questions.reduce((n, q) => n + statementSubAnswers(q), 0),
			0,
		)
		return {
			earned: round2((score?.correct ?? 0) * POINTS_PER_SUB_ANSWER),
			max: round2(subAnswers * POINTS_PER_SUB_ANSWER),
		}
	}
	const earned =
		score && score.total > 0
			? (score.correct / score.total) * POINTS_PER_QUESTION
			: 0
	return { earned: round2(earned), max: POINTS_PER_QUESTION }
}

/** The two sections of the exam, which are practised separately. */
type TrainingMode = "knowledge" | "listening"

const MODE_LABELS: Record<TrainingMode, string> = {
	knowledge: "Γνώσεις",
	listening: "Ακουστικά",
}

const SELECT_CLASS =
	"w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"

type TrainingProps = {
	categories: CategoryOption[]
	data: QuizData | null
}

function TrainingSetup({ categories }: { categories: CategoryOption[] }) {
	const [mode, setMode] = useState<TrainingMode>("knowledge")
	const [categories_selected, setCategoriesSelected] = useState<string[]>([])
	const [amount, setAmount] = useState("10")
	const [quizType, setQuizType] = useState("")

	// The listening category holds nothing but audio clips, which are reached
	// through the Ακουστικά mode — offering it as a knowledge subject would only
	// ever produce an empty test.
	const categoryOptions = categories
		.filter((c) => c.value !== QuizCategory.LISTENING)
		.map((c) => ({
			value: c.value,
			label: QUIZ_CATEGORY_LABELS[c.value as QuizCategory] ?? c.label,
		}))

	function handleStart() {
		const params: Record<string, string> = { amount }
		if (mode === "listening") {
			// The listening section is asked for by question type, not by subject:
			// the clips are one pool, so there is no category to narrow it by.
			params.quiz_type = "Listening"
		} else {
			if (categories_selected.length > 0) {
				params.category = categories_selected.join(",")
			}
			if (quizType) {
				params.quiz_type = quizType
			}
		}
		router.get("/quiz/training", params, { preserveState: false })
	}

	return (
		<section className="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-sm sm:p-8">
			<h1 className="mb-6 text-2xl font-bold">Τεστ προσομοίωσης</h1>

			<div className="mb-4">
				<label
					htmlFor="mode"
					className="mb-1 block text-sm font-medium text-gray-700"
				>
					Είδος εξάσκησης
				</label>
				<select
					id="mode"
					value={mode}
					onChange={(e) => setMode(e.target.value as TrainingMode)}
					className={SELECT_CLASS}
				>
					<option value="knowledge">{MODE_LABELS.knowledge}</option>
					<option value="listening">{MODE_LABELS.listening}</option>
				</select>
			</div>

			{/* The subject and the question type only narrow the knowledge pool —
			    the listening section is a single pool of clips. */}
			{mode === "knowledge" && (
				<>
					<div className="mb-4">
						<label
							htmlFor="category"
							className="mb-1 block text-sm font-medium text-gray-700"
						>
							Κατηγορία
						</label>
						<MultiSelect
							options={categoryOptions}
							selected={categories_selected}
							onChange={setCategoriesSelected}
							placeholder="Όλες οι κατηγορίες"
						/>
					</div>

					{import.meta.env.DEV && (
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
								className={SELECT_CLASS}
							>
								<option value="">Όλοι οι τύποι</option>
								<option value="Statement">
									Σωστό / Λάθος & Πολλαπλής επιλογής
								</option>
								<option value="DragAndDrop">Κατάταξη</option>
								<option value="Matching">Αντιστοίχηση</option>
								<option value="FillInTheBlank">Συμπλήρωση κενού</option>
								<option value="OpenEnded">Ανοιχτή ερώτηση</option>
								<option value="MapPointer">Χάρτης</option>
							</select>
						</div>
					)}
				</>
			)}

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
					className={SELECT_CLASS}
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

function TrainingSession({ data }: { data: QuizData }) {
	const [currentIndex, setCurrentIndex] = useState(0)
	const [validatedSet, setValidatedSet] = useState<Set<number>>(new Set())
	const allValidatedEarly = validatedSet.size === data.length
	const { exitConfirmOpen, exitConfirmCancel, exitConfirmConfirm } =
		useExitConfirmation(!allValidatedEarly)
	const scoresRef = useRef<Map<number, Score>>(new Map())
	const [scoreVersion, setScoreVersion] = useState(0)

	const scoreCallbacks = useMemo(
		() =>
			data.map((_, index) => (correct: number, total: number) => {
				scoresRef.current.set(index, { correct, total })
				setScoreVersion((v) => v + 1)
			}),
		[data],
	)

	// A question's maximum depends on its type — a listening clip is worth as
	// much as its sub-answers add up to, not the flat two points of a knowledge
	// question — so the total is summed per question rather than multiplied.
	const { earnedPoints, maxPoints, earnedUpToCurrent, maxUpToCurrent } =
		useMemo(() => {
			void scoreVersion
			let earned = 0
			let earnedUpto = 0
			let max = 0
			let maxUpto = 0
			data.forEach((item, idx) => {
				const points = questionPoints(item, scoresRef.current.get(idx))
				earned += points.earned
				max += points.max
				if (idx <= currentIndex) {
					earnedUpto += points.earned
					maxUpto += points.max
				}
			})
			return {
				earnedPoints: round2(earned),
				maxPoints: round2(max),
				earnedUpToCurrent: round2(earnedUpto),
				maxUpToCurrent: round2(maxUpto),
			}
		}, [scoreVersion, data, currentIndex])

	const total = data.length
	const isFirst = currentIndex === 0
	const isLast = currentIndex === total - 1
	const isCurrentValidated = validatedSet.has(currentIndex)
	const allValidated = validatedSet.size === total

	const handleValidate = useCallback(() => {
		setValidatedSet((prev) => new Set(prev).add(currentIndex))
	}, [currentIndex])

	const goNext = useCallback(() => {
		if (currentIndex < total - 1) {
			setCurrentIndex((i) => i + 1)
		}
	}, [currentIndex, total])

	const goPrev = useCallback(() => {
		if (currentIndex > 0) {
			setCurrentIndex((i) => i - 1)
		}
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
			<ExitConfirmDialog
				open={exitConfirmOpen}
				onCancel={exitConfirmCancel}
				onConfirm={exitConfirmConfirm}
			/>
			{allValidated && (
				<ResultsBanner
					earnedPoints={earnedPoints}
					maxPoints={maxPoints}
					buttonLabel="Νέο τεστ"
					onReset={() => router.get("/quiz/training")}
				/>
			)}

			{!allValidated && (
				<div className="shrink-0 rounded-2xl bg-white p-4 shadow-sm">
					<div className="mb-2 flex items-center justify-between text-sm text-gray-600">
						<span>
							Ερώτηση {currentIndex + 1} από {total}
						</span>
						<span className="text-sm font-medium text-blue-600">
							Βαθμολογία: {earnedUpToCurrent} / {maxUpToCurrent}
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

			<div
				className={`${allValidated ? "space-y-4" : "min-h-0 flex-1 overflow-hidden"} py-1`}
			>
				{data.map((item, idx) => {
					const score = scoresRef.current.get(idx)
					const { earned, max } = questionPoints(item, score)
					const ratio = max > 0 ? earned / max : 0
					// Every question stays mounted so its answers survive going back and
					// forth; only the current one is on screen, and once the test is over
					// they all are, as a list to review.
					const isVisible = allValidated || idx === currentIndex
					return (
						<div
							key={`${item.quiz_type}-${item.id}`}
							className={!isVisible ? "hidden" : !allValidated ? "h-full" : ""}
						>
							<QuizRenderer
								item={item}
								index={idx + 1}
								active={isVisible}
								forceValidation={validatedSet.has(idx)}
								onScore={scoreCallbacks[idx]}
								badge={
									allValidated && score ? (
										<span
											className="text-sm font-bold"
											style={{ color: getScoreColor(ratio) }}
										>
											{earned} / {max}
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

export default function Training({ categories, data }: TrainingProps) {
	if (!data) {
		return <TrainingSetup categories={categories} />
	}
	return <TrainingSession data={data} />
}
