import { router } from "@inertiajs/react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import DragAndDrop from "@/components/quiz/DragAndDrop"
import FillInTheBlank from "@/components/quiz/FillInTheBlank"
import MultipleChoice from "@/components/quiz/MultipleChoice"
import OpenEnded from "@/components/quiz/OpenEnded"
import TrueFalse from "@/components/quiz/TrueFalse"
import { Button } from "@/components/ui/button"
import type {
	DragAndDropContent,
	DragAndDropModel,
	FillInTheBlankContent,
	FillInTheBlankModel,
	OpenEndedContent,
	OpenEndedModel,
	StatementModel,
	TrainingData,
} from "@/types/models"

const SIMULATION_DURATION = 30 * 60 // 30 minutes in seconds

type SimulationProps = {
	data: TrainingData | null
}

function QuizRenderer({
	item,
	index,
	forceValidation,
	onScore,
}: {
	item: TrainingData[number]
	index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}) {
	switch (item.quiz_type) {
		case "Statement": {
			const statementItem = {
				id: item.id,
				category: item.category,
				content: item.content,
				type:
					"choices" in item.content &&
					Array.isArray(item.content.choices) &&
					item.content.choices.length === 2
						? "TRUE_FALSE"
						: "MULTIPLE_CHOICE",
			} as StatementModel
			if (statementItem.type === "TRUE_FALSE") {
				return (
					<TrueFalse
						item={statementItem}
						item_index={index}
						forceValidation={forceValidation}
						onScore={onScore}
					/>
				)
			}
			return (
				<MultipleChoice
					item={statementItem}
					item_index={index}
					forceValidation={forceValidation}
					onScore={onScore}
				/>
			)
		}
		case "DragAndDrop": {
			const dndItem = {
				id: item.id,
				category: item.category,
				content: item.content as DragAndDropContent,
			} as DragAndDropModel
			return (
				<DragAndDrop
					item={dndItem}
					forceValidation={forceValidation}
					onScore={onScore}
				/>
			)
		}
		case "OpenEnded": {
			const openEndedItem = {
				id: item.id,
				category: item.category,
				content: item.content as OpenEndedContent,
			} as OpenEndedModel
			return (
				<OpenEnded
					item={openEndedItem}
					item_index={index}
					forceValidation={forceValidation}
					onScore={onScore}
				/>
			)
		}
		case "FillInTheBlank": {
			const fitbItem = {
				id: item.id,
				category: item.category,
				content: item.content as FillInTheBlankContent,
			} as FillInTheBlankModel
			return (
				<FillInTheBlank
					item={fitbItem}
					item_index={index}
					forceValidation={forceValidation}
					onScore={onScore}
				/>
			)
		}
		default:
			return (
				<div className="rounded-lg border p-4 text-sm text-gray-500">
					Μη υποστηριζόμενος τύπος ερώτησης: {item.quiz_type}
				</div>
			)
	}
}

function formatTime(seconds: number): string {
	const m = Math.floor(seconds / 60)
	const s = seconds % 60
	return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
}

function SimulationSession({ data }: { data: TrainingData }) {
	const [currentIndex, setCurrentIndex] = useState(0)
	const [finished, setFinished] = useState(false)
	const [timeLeft, setTimeLeft] = useState(SIMULATION_DURATION)
	const scoresRef = useRef<Map<number, { correct: number; total: number }>>(
		new Map(),
	)
	const [scoreVersion, setScoreVersion] = useState(0)

	const POINTS_PER_QUESTION = 2

	// Timer
	useEffect(() => {
		if (finished) return
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
		if (currentIndex < total - 1) setCurrentIndex((i) => i + 1)
	}, [currentIndex, total])

	const goPrev = useCallback(() => {
		if (currentIndex > 0) setCurrentIndex((i) => i - 1)
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
		<section className="flex h-full flex-col">
			{finished && (
				<div className="rounded-2xl bg-white p-6 text-center shadow-sm">
					<h1 className="mb-2 text-2xl font-bold">Αποτελέσματα</h1>
					<p className="mb-2 text-3xl font-bold text-blue-600">
						{earnedPoints} / {maxPoints}
					</p>
					<p className="mb-4 text-sm text-gray-600">
						Δείτε τις σωστές και λάθος απαντήσεις σας παρακάτω.
					</p>
					<Button
						variant="outline"
						onClick={() => router.get("/quiz/simulation")}
					>
						Νέα προσομοίωση
					</Button>
				</div>
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

			<div className="min-h-0 flex-1 py-4">
				{data.map((item, idx) => (
					<div
						key={`${item.quiz_type}-${item.id}`}
						className={!finished && idx !== currentIndex ? "hidden" : "h-full"}
					>
						<QuizRenderer
							item={item}
							index={idx + 1}
							forceValidation={finished}
							onScore={scoreCallbacks[idx]}
						/>
					</div>
				))}
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
					40 τυχαίες ερωτήσεις από όλες τις κατηγορίες. Έχετε 30 λεπτά στη
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
