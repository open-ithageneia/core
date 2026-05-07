import { router } from "@inertiajs/react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ExitConfirmDialog } from "@/components/exit-confirm-dialog"
import { QuizRenderer } from "@/components/quiz/quiz-renderer"
import { ResultsBanner } from "@/components/quiz/shared/results-banner"
import { Button } from "@/components/ui/button"
import { useExitConfirmation } from "@/hooks/use-exit-confirmation"
import { getScoreColor } from "@/lib/score-color"
import type { TrainingData } from "@/types/models"

const SIMULATION_DURATION = 30 * 60 // 30 minutes in seconds

type SimulationProps = {
	data: TrainingData | null
}

function formatTime(seconds: number): string {
	const m = Math.floor(seconds / 60)
	const s = seconds % 60
	return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
}

function SimulationSession({ data }: { data: TrainingData }) {
	const [currentIndex, setCurrentIndex] = useState(0)
	const [finished, setFinished] = useState(false)
	const { exitConfirmOpen, exitConfirmCancel, exitConfirmConfirm } =
		useExitConfirmation(!finished)
	const [timeLeft, setTimeLeft] = useState(SIMULATION_DURATION)
	const scoresRef = useRef<Map<number, { correct: number; total: number }>>(
		new Map(),
	)
	const [scoreVersion, setScoreVersion] = useState(0)

	const POINTS_PER_QUESTION = 2

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
		const max = data.length * POINTS_PER_QUESTION
		for (const { correct, total } of scoresRef.current.values()) {
			earned += total > 0 ? (correct / total) * POINTS_PER_QUESTION : 0
		}
		return { earnedPoints: Math.round(earned * 100) / 100, maxPoints: max }
	}, [scoreVersion, data.length])

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
				<Button onClick={() => router.get("/quiz/simulation")}>Πίσω</Button>
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
					onReset={() => router.get("/quiz/simulation")}
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

			<div className={`${finished ? "space-y-4" : "min-h-0 flex-1"} py-1`}>
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
											{earned} / {POINTS_PER_QUESTION}
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

export default function Simulation({ data }: SimulationProps) {
	if (!data) {
		return (
			<section className="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-sm sm:p-8">
				<h1 className="mb-6 text-2xl font-bold">Προσομοίωση εξέτασης</h1>
				<p className="mb-4 text-sm text-gray-600">
					20 τυχαίες ερωτήσεις από όλες τις κατηγορίες. Έχετε 30 λεπτά στη
					διάθεσή σας.
				</p>

				<Button
					onClick={() =>
						router.get(
							"/quiz/simulation",
							{ start: "1" },
							{ preserveState: false },
						)
					}
					className="w-full"
				>
					Ξεκινήστε
				</Button>
			</section>
		)
	}
	return <SimulationSession data={data} />
}
