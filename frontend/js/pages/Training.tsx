import { router } from "@inertiajs/react"
import { useCallback, useMemo, useRef, useState } from "react"
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

type CategoryOption = {
	value: string
	label: string
}

type TrainingProps = {
	categories: CategoryOption[]
	data: TrainingData | null
}

function TrainingSetup({ categories }: { categories: CategoryOption[] }) {
	const [category, setCategory] = useState("")
	const [amount, setAmount] = useState("10")

	function handleStart() {
		const params: Record<string, string> = { amount }
		if (category) params.category = category
		router.get("/quiz/training", params, { preserveState: false })
	}

	return (
		<section className="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-sm sm:p-8">
			<h1 className="mb-6 text-2xl font-bold">Τεστ προσομοίωσης</h1>

			<div className="mb-4">
				<label
					htmlFor="category"
					className="mb-1 block text-sm font-medium text-gray-700"
				>
					Κατηγορία
				</label>
				<select
					id="category"
					value={category}
					onChange={(e) => setCategory(e.target.value)}
					className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
				>
					<option value="">Όλες οι κατηγορίες</option>
					{categories.map((c) => (
						<option key={c.value} value={c.value}>
							{c.label}
						</option>
					))}
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

function TrainingSession({ data }: { data: TrainingData }) {
	const [currentIndex, setCurrentIndex] = useState(0)
	const [finished, setFinished] = useState(false)
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

	const { earnedPoints, maxPoints } = useMemo(() => {
		// Force recalc when scoreVersion changes
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
		<section className="space-y-4">
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
						onClick={() => router.get("/quiz/training")}
					>
						Νέο τεστ
					</Button>
				</div>
			)}

			{!finished && (
				<div className="rounded-2xl bg-white p-4 shadow-sm">
					<div className="mb-2 flex items-center justify-between text-sm text-gray-600">
						<span>
							Ερώτηση {currentIndex + 1} από {total}
						</span>
						<span className="text-xs uppercase tracking-wide text-gray-400">
							{data[currentIndex].quiz_type}
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

			{/* Render all components — hide non-current with CSS to preserve state */}
			{data.map((item, idx) => (
				<div
					key={`${item.quiz_type}-${item.id}`}
					className={!finished && idx !== currentIndex ? "hidden" : undefined}
				>
					<QuizRenderer
						item={item}
						index={idx + 1}
						forceValidation={!!finished}
						onScore={scoreCallbacks[idx]}
					/>
				</div>
			))}

			{!finished && (
				<div className="flex items-center justify-between rounded-2xl bg-white p-4 shadow-sm">
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

export default function Training({ categories, data }: TrainingProps) {
	if (!data) {
		return <TrainingSetup categories={categories} />
	}
	return <TrainingSession data={data} />
}
