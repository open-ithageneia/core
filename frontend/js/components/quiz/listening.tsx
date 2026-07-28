import { useCallback, useEffect, useMemo, useState } from "react"
import MultipleChoice from "@/components/quiz/multiple-choice"
import QuizCard from "@/components/quiz/shared/quiz-card"
import ValidationButton from "@/components/quiz/shared/validation-button"
import TrueFalse from "@/components/quiz/true-false"
import { useValidation } from "@/hooks/quiz/use-validation"
import {
	LISTENING_PART_LABELS,
	LISTENING_PART_LETTERS,
	QUIZ_INSTRUCTIONS,
	StatementType,
} from "@/types/enums"
import type {
	ListeningModel,
	ListeningPartGroup,
	StatementModel,
} from "@/types/models"

type Score = { correct: number; total: number }
type Reporter = (correct: number, total: number) => void

type ListeningProps = {
	item: ListeningModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

function QuestionPart({
	item,
	forceValidation,
	onScore,
}: {
	item: StatementModel
	forceValidation: boolean
	onScore: Reporter
}) {
	const Component =
		item.type === StatementType.TRUE_FALSE ? TrueFalse : MultipleChoice
	return (
		<Component
			bare
			item={item}
			item_index={0}
			forceValidation={forceValidation}
			onScore={onScore}
		/>
	)
}

/**
 * One part of a listening question, as a panel with its own header so the
 * sections read as separate exercises. The chrome is deliberately monochrome:
 * green, red and blue already mean "correct", "wrong" and "your answer" inside
 * these cards, so colouring the parts would collide with that.
 */
function PartSection({
	part,
	showValidation,
	reporters,
}: {
	part: ListeningPartGroup
	showValidation: boolean
	reporters: Record<number, Reporter>
}) {
	const isNumbered = part.questions.length > 1

	return (
		<section className="overflow-hidden rounded-xl border">
			<header className="flex items-center gap-2 border-b bg-muted/60 px-3 py-2">
				<span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-foreground text-xs font-bold text-background">
					{LISTENING_PART_LETTERS[part.part]}
				</span>
				<h3 className="text-sm font-semibold">
					{LISTENING_PART_LABELS[part.part]}
				</h3>
			</header>

			<div className="divide-y">
				{part.questions.map((question, index) => (
					<div key={question.id} className="flex gap-3 p-3">
						{isNumbered && (
							<span className="mt-0.5 shrink-0 text-xs font-semibold text-muted-foreground tabular-nums">
								{index + 1}.
							</span>
						)}
						<div className="min-w-0 flex-1">
							<QuestionPart
								item={question}
								forceValidation={showValidation}
								onScore={reporters[question.id]}
							/>
						</div>
					</div>
				))}
			</div>
		</section>
	)
}

/**
 * Renders an audio comprehension question: the clip is played from the card
 * header (a limited number of times), and its questions — grouped into parts A
 * and B — share a single "validate" button. Their scores are summed into one
 * result for the question.
 */
export default function Listening({
	item,
	item_index,
	forceValidation,
	onScore,
}: ListeningProps) {
	const { showValidation, setShowValidation, showValidationButton } =
		useValidation({ forceValidation })

	const [scores, setScores] = useState<Record<number, Score>>({})

	const reportScore = useCallback(
		(id: number, correct: number, total: number) =>
			setScores((prev) => ({ ...prev, [id]: { correct, total } })),
		[],
	)

	// One stable callback per question: the questions report their score from an
	// effect keyed on the callback identity, so a fresh function each render would
	// make them report in a loop. Keyed by id so the parts split doesn't matter.
	const reporters = useMemo(() => {
		const byId: Record<number, Reporter> = {}
		for (const part of item.parts) {
			for (const question of part.questions) {
				byId[question.id] = (correct, total) =>
					reportScore(question.id, correct, total)
			}
		}
		return byId
	}, [item.parts, reportScore])

	const { correct, total } = useMemo(() => {
		let correct = 0
		let total = 0
		for (const score of Object.values(scores)) {
			correct += score.correct
			total += score.total
		}
		return { correct, total }
	}, [scores])

	useEffect(() => {
		if (showValidation && onScore) {
			onScore(correct, total)
		}
	}, [showValidation, onScore, correct, total])

	return (
		<QuizCard
			title={`Ερώτηση ${item_index}`}
			category={item.category}
			instruction={QUIZ_INSTRUCTIONS.LISTENING}
			promptAudioUrl={item.audio_url ?? undefined}
			promptAudioMaxPlays={item.max_plays}
		>
			<div className="space-y-4">
				{item.parts.map((part) => (
					<PartSection
						key={part.part}
						part={part}
						showValidation={showValidation}
						reporters={reporters}
					/>
				))}
			</div>

			{showValidation && item.transcript && (
				<div className="mt-3 rounded-lg border bg-muted/50 p-3">
					<p className="mb-1 text-xs font-medium text-muted-foreground">
						Κείμενο ηχητικού
					</p>
					<p className="whitespace-pre-line text-sm">{item.transcript}</p>
				</div>
			)}

			{showValidationButton && (
				<div className="mt-3">
					<ValidationButton
						showValidation={showValidation}
						onValidate={() => setShowValidation(true)}
					/>
				</div>
			)}
		</QuizCard>
	)
}
