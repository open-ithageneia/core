import { DragDropProvider } from "@dnd-kit/react"
import { useEffect } from "react"
import DraggableChip from "@/components/quiz/shared/DraggableChip"
import DroppableCell from "@/components/quiz/shared/DroppableCell"
import QuizCard from "@/components/quiz/shared/QuizCard"
import QuizScore from "@/components/quiz/shared/QuizScore"
import ValidationButton from "@/components/quiz/shared/ValidationButton"
import { Input } from "@/components/ui/input"
import { useFillInTheBlank } from "@/hooks/useFillInTheBlank"
import { cn } from "@/lib/utils"
import { QUIZ_INSTRUCTIONS, ValidationStatus } from "@/types/enums"
import type { FillInTheBlankModel } from "@/types/models"

type FillInTheBlankProps = {
	item: FillInTheBlankModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

export default function FillInTheBlank({
	item,
	item_index,
	forceValidation,
	onScore,
}: FillInTheBlankProps) {
	const {
		content,
		blanks,
		answers,
		updateAnswer,
		showValidation,
		setShowValidation,
		showValidationButton,
		hasAtLeastOneAnswer,
		allBlanksFilledDnd,
		states,
		correctAnswersCount,
		variant,
		availableValues,
		droppedValues,
		clearDroppedValue,
		handleDragEnd,
	} = useFillInTheBlank(item, { forceValidation })

	useEffect(() => {
		if (showValidation && onScore) {
			onScore(correctAnswersCount, blanks.length)
		}
	}, [showValidation, onScore, correctAnswersCount, blanks.length])

	// Map (textIndex, partIndex) → flat blank index for lookup
	let blankCounter = 0
	const getBlankIndex = () => blankCounter++

	const canValidate =
		variant === "choices_shown" ? allBlanksFilledDnd : hasAtLeastOneAnswer

	const renderTexts = () => {
		// Reset counter each render
		blankCounter = 0

		return (
			<div className="space-y-4">
				{content.texts.map((text, textIndex) => (
					<div
						key={`text-${textIndex}`}
						className="flex flex-wrap items-center gap-1.5 leading-relaxed"
					>
						{text.parts.map((part, partIndex) => {
							if (!part.is_blank) {
								return (
									<span key={`part-${textIndex}-${partIndex}`}>
										{part.text}
									</span>
								)
							}

							const bi = getBlankIndex()
							const state = states[bi]

							// --- Variant: inline_choices (dropdown) ---
							if (variant === "inline_choices" && part.choices) {
								return (
									<span
										key={`part-${textIndex}-${partIndex}`}
										className="inline-flex items-center gap-1"
									>
										<select
											value={answers[bi]}
											onChange={(e) => updateAnswer(bi, e.target.value)}
											disabled={showValidation}
											className={cn(
												"inline-block min-w-30 rounded-md border px-2 py-1 text-sm",
												showValidation &&
													state === ValidationStatus.Correct &&
													"border-green-500 bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-300",
												showValidation &&
													state === ValidationStatus.Incorrect &&
													"border-red-500 bg-red-50 text-red-800 line-through dark:bg-red-950 dark:text-red-300",
											)}
										>
											<option value="">—</option>
											{part.choices.map((c, ci) => (
												<option key={ci} value={c.text}>
													{c.text}
												</option>
											))}
										</select>
										{showValidation && state === ValidationStatus.Incorrect && (
											<span className="text-sm font-medium text-green-700 dark:text-green-400">
												{part.choices
													.filter((c) => c.is_correct)
													.map((c) => c.text)
													.join(" / ")}
											</span>
										)}
									</span>
								)
							}

							// --- Variant: choices_shown (drag & drop drop zone) ---
							if (variant === "choices_shown") {
								return (
									<span
										key={`part-${textIndex}-${partIndex}`}
										className="inline-flex items-center gap-1"
									>
										<DroppableCell
											id={`blank-${bi}`}
											value={droppedValues[bi]}
											disabled={droppedValues[bi] !== null}
											validationState={state}
											isLocked={showValidation}
											onRemove={() => clearDroppedValue(bi)}
										/>
										{showValidation && state === ValidationStatus.Incorrect && (
											<span className="text-sm font-medium text-green-700 dark:text-green-400">
												{blanks[bi].choices
													.filter((c) => c.is_correct)
													.map((c) => c.text)
													.join(" / ")}
											</span>
										)}
									</span>
								)
							}

							// --- Variant: hidden (text input, normalized comparison) ---
							return (
								<span
									key={`part-${textIndex}-${partIndex}`}
									className="inline-flex items-center gap-1"
								>
									<Input
										type="text"
										placeholder="..."
										value={answers[bi]}
										onChange={(e) => updateAnswer(bi, e.target.value)}
										disabled={showValidation}
										className={cn(
											"inline-block w-32",
											showValidation &&
												state === ValidationStatus.Correct &&
												"border-green-500 bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-300",
											showValidation &&
												state === ValidationStatus.Incorrect &&
												"border-red-500 bg-red-50 text-red-800 line-through dark:bg-red-950 dark:text-red-300",
										)}
									/>
									{showValidation && state === ValidationStatus.Incorrect && (
										<span className="text-sm font-medium text-green-700 dark:text-green-400">
											{blanks[bi].choices
												.filter((c) => c.is_correct)
												.map((c) => c.text)
												.join(" / ")}
										</span>
									)}
								</span>
							)
						})}
					</div>
				))}
			</div>
		)
	}

	const body = (
		<>
			{renderTexts()}

			{canValidate && showValidationButton && (
				<div className="mt-3">
					<ValidationButton
						showValidation={showValidation}
						onValidate={() => setShowValidation(true)}
					/>
				</div>
			)}

			<QuizScore
				correctAnswersCount={correctAnswersCount}
				totalSubAnswers={blanks.length}
				showValidation={showValidation}
			/>
		</>
	)

	// Wrap in DragDropProvider only for choices_shown variant
	if (variant === "choices_shown") {
		return (
			<QuizCard
				title={`Ερώτηση ${item_index}`}
				instruction={QUIZ_INSTRUCTIONS.FILL_IN_THE_BLANK}
				promptAssetUrl={content.prompt_asset_url}
			>
				<DragDropProvider
					onDragEnd={({ operation }) => {
						if (!operation.source || !operation.target) return
						handleDragEnd(
							operation.source.data.value,
							String(operation.target.id),
						)
					}}
				>
					<div className="rounded-xl border bg-muted/30 p-4">
						<div className="flex flex-wrap gap-2">
							{availableValues.map((value) => (
								<DraggableChip
									key={value}
									id={`fitb-chip-${value}`}
									value={value}
									disabled={showValidation}
								/>
							))}
							{availableValues.length === 0 && !showValidation && (
								<span className="text-sm text-muted-foreground">
									Όλες οι λέξεις έχουν τοποθετηθεί
								</span>
							)}
						</div>
					</div>

					{body}
				</DragDropProvider>
			</QuizCard>
		)
	}

	return (
		<QuizCard
			title={`Ερώτηση ${item_index}`}
			instruction={QUIZ_INSTRUCTIONS.FILL_IN_THE_BLANK}
			promptAssetUrl={content.prompt_asset_url}
		>
			{body}
		</QuizCard>
	)
}
