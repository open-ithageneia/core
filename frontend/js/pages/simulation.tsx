import { router, usePage } from "@inertiajs/react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ExitConfirmDialog } from "@/components/exit-confirm-dialog"
import { QuizRenderer } from "@/components/quiz/quiz-renderer"
import { ResultsBanner } from "@/components/quiz/shared/results-banner"
import { Button } from "@/components/ui/button"
import { useExitConfirmation } from "@/hooks/use-exit-confirmation"
import { getScoreColor } from "@/lib/score-color"
import type { QuizData } from "@/types/models"

type SimulationVariant = "knowledge" | "listening"

/** Time allowed per variant, in seconds. */
const SIMULATION_DURATION: Record<SimulationVariant, number> = {
	knowledge: 30 * 60,
	listening: 15 * 60,
}

type SimulationProps = {
	data: QuizData | null
	variant?: SimulationVariant
}

// Knowledge questions are worth a flat 2 points each, shared proportionally
// between their sub-answers.
const POINTS_PER_QUESTION = 2
// The listening exam is a single question, so its score comes straight from the
// sub-answers: 1.5 points each (e.g. 5 true/false + 5 multiple choice → 15).
const POINTS_PER_SUB_ANSWER = 1.5

type Score = { correct: number; total: number }

function round2(value: number): number {
	return Math.round(value * 100) / 100
}

/** Points earned and available for a single question, per scoring mode. */
function questionPoints(
	score: Score | undefined,
	perSubAnswer: boolean,
): { earned: number; max: number } {
	if (perSubAnswer) {
		return {
			earned: round2((score?.correct ?? 0) * POINTS_PER_SUB_ANSWER),
			max: round2((score?.total ?? 0) * POINTS_PER_SUB_ANSWER),
		}
	}
	const earned =
		score && score.total > 0
			? (score.correct / score.total) * POINTS_PER_QUESTION
			: 0
	return { earned: round2(earned), max: POINTS_PER_QUESTION }
}

function formatTime(seconds: number): string {
	const m = Math.floor(seconds / 60)
	const s = seconds % 60
	return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
}

function SimulationSession({
	data,
	basePath,
	variant,
}: {
	data: QuizData
	basePath: string
	variant: SimulationVariant
}) {
	const [currentIndex, setCurrentIndex] = useState(0)
	const [finished, setFinished] = useState(false)
	// No questions means there is no session to protect: keep the interceptor
	// off so the empty state's navigation isn't swallowed by a dialog that the
	// empty branch never renders.
	const { exitConfirmOpen, exitConfirmCancel, exitConfirmConfirm } =
		useExitConfirmation(!finished && data.length > 0)
	const [timeLeft, setTimeLeft] = useState(SIMULATION_DURATION[variant])
	const scoresRef = useRef<Map<number, Score>>(new Map())
	const [scoreVersion, setScoreVersion] = useState(0)

	const perSubAnswer = variant === "listening"

	// Timer
	useEffect(() => {
		if (finished) {
			return
		}
		const interval = setInterval(() => {
			setTimeLeft((prev) => {
				if (prev <= 1) {
					clearInterval(interval)
					setFinished(true)
					return 0
				}
				return prev - 1
			})
		}, 1000)
		return () => clearInterval(interval)
	}, [finished])

	const scoreCallbacks = useMemo(
		() =>
			data.map((_, index) => (correct: number, total: number) => {
				scoresRef.current.set(index, { correct, total })
				setScoreVersion((v) => v + 1)
			}),
		[data],
	)

	const { earnedPoints, maxPoints } = useMemo(() => {
		void scoreVersion
		let earned = 0
		// Per-question scoring knows the maximum up front; per-sub-answer scoring
		// only learns how many sub-answers a question has once it reports a score,
		// which happens for every question the moment the simulation finishes.
		let max = perSubAnswer ? 0 : data.length * POINTS_PER_QUESTION
		for (let index = 0; index < data.length; index++) {
			const points = questionPoints(scoresRef.current.get(index), perSubAnswer)
			earned += points.earned
			if (perSubAnswer) {
				max += points.max
			}
		}
		return { earnedPoints: round2(earned), maxPoints: round2(max) }
	}, [scoreVersion, data.length, perSubAnswer])

	const total = data.length
	const isFirst = currentIndex === 0
	const isLast = currentIndex === total - 1

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
				<p className="mb-4 text-sm text-gray-600">Δοκιμάστε ξανά αργότερα.</p>
				<Button onClick={() => router.get(basePath)}>Πίσω</Button>
			</section>
		)
	}

	const timerWarning = timeLeft <= 5 * 60

	return (
		<section className={`flex ${finished ? "" : "h-full"} flex-col`}>
			<ExitConfirmDialog
				open={exitConfirmOpen}
				onCancel={exitConfirmCancel}
				onConfirm={exitConfirmConfirm}
			/>
			{finished && (
				<ResultsBanner
					earnedPoints={earnedPoints}
					maxPoints={maxPoints}
					buttonLabel="Νέα προσομοίωση"
					onReset={() => router.get(basePath)}
				/>
			)}

			{!finished && (
				<div className="shrink-0 rounded-2xl bg-white p-4 shadow-sm">
					<div className="mb-2 flex items-center justify-between text-sm text-gray-600">
						<span>
							Ερώτηση {currentIndex + 1} από {total}
						</span>
						<span
							className={`font-mono text-lg font-bold ${timerWarning ? "text-red-600" : "text-gray-700"}`}
						>
							⏱ {formatTime(timeLeft)}
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
				className={`${finished ? "space-y-4" : "min-h-0 flex-1 overflow-hidden"} py-1`}
			>
				{data.map((item, idx) => {
					const score = scoresRef.current.get(idx)
					const { earned, max } = questionPoints(score, perSubAnswer)
					const ratio = max > 0 ? earned / max : 0
					return (
						<div
							key={`${item.quiz_type}-${item.id}`}
							className={
								!finished && idx !== currentIndex
									? "hidden"
									: !finished
										? "h-full"
										: ""
							}
						>
							<QuizRenderer
								item={item}
								index={idx + 1}
								forceValidation={finished}
								onScore={scoreCallbacks[idx]}
								badge={
									finished && score ? (
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

			{!finished && (
				<div className="sticky bottom-0 flex shrink-0 items-center justify-between rounded-2xl bg-white p-4 shadow-sm">
					<Button variant="outline" onClick={goPrev} disabled={isFirst}>
						← Προηγούμενη
					</Button>

					{isLast ? (
						<Button onClick={() => setFinished(true)}>Ολοκλήρωση</Button>
					) : (
						<Button onClick={goNext}>Επόμενη →</Button>
					)}
				</div>
			)}
		</section>
	)
}

export default function Simulation({
	data,
	variant = "knowledge",
}: SimulationProps) {
	// Current path without query params, so back/reset restart the same
	// simulation mode (e.g. /quiz/simulation/knowledge), which redirects to the
	// mode picker when hit without `?start`.
	const basePath = usePage().url.split("?")[0]

	if (!data) {
		return null
	}
	return <SimulationSession data={data} basePath={basePath} variant={variant} />
}
