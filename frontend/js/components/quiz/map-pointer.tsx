import { useEffect } from "react"
import GreeceMap from "@/components/quiz/shared/greece-map"
import QuizCard from "@/components/quiz/shared/quiz-card"
import RemoveAnswerButton from "@/components/quiz/shared/remove-answer-button"
import ValidationButton from "@/components/quiz/shared/validation-button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { useMapPointer } from "@/hooks/quiz/use-map-pointer"
import { cn } from "@/lib/utils"
import { QUIZ_INSTRUCTIONS } from "@/types/enums"
import type { MapPointerModel } from "@/types/models"

type MapPointerProps = {
	item: MapPointerModel
	item_index: number
	forceValidation?: boolean
	onScore?: (correct: number, total: number) => void
}

export default function MapPointer({
	item,
	item_index,
	forceValidation,
	onScore,
}: MapPointerProps) {
	const {
		isDropMode,
		showValidation,
		setShowValidation,
		showValidationButton,
		totalScore,
		correctAnswersCount,
		allRegionIds,
		// Drop mode
		availableLabels,
		selectedLabel,
		isDropComplete,
		dropValidationMap,
		dropRegionLabels,
		handleRegionClick,
		toggleLabelSelection,
		// Type mode
		selectedTypeRegion,
		typeAnswers,
		hasAtLeastOneAnswer,
		typeValidationMap,
		typeRegionLabels,
		handleTypeRegionClick,
		updateTypeAnswer,
		clearTypeAnswer,
	} = useMapPointer(item, { forceValidation })

	useEffect(() => {
		if (showValidation && onScore) {
			onScore(correctAnswersCount, totalScore)
		}
	}, [showValidation, onScore, correctAnswersCount, totalScore])

	// Every region takes a label, including ones that already hold others: two
	// answers sharing a polygon both have to be placeable on it.
	const activeRegionIds = allRegionIds

	return (
		<QuizCard
			title={`Ερώτηση ${item_index}`}
			category={item.category}
			instruction={QUIZ_INSTRUCTIONS.MAP_POINTER}
			promptText={item.content.prompt_text}
		>
			{isDropMode ? (
				<>
					{/* Choices bank */}
					<div className="rounded-xl border bg-muted/30 p-2">
						<div className="flex flex-wrap items-center gap-1.5">
							{availableLabels.map((label, idx) => (
								<button
									key={`label-${label}-${idx}`}
									type="button"
									disabled={showValidation}
									onClick={() => toggleLabelSelection(label)}
									className={cn(
										"shrink-0 select-none rounded-2xl transition-colors",
										showValidation
											? "cursor-not-allowed opacity-60"
											: "cursor-pointer",
									)}
								>
									<Badge
										variant={selectedLabel === label ? "default" : "secondary"}
										className={cn(
											"rounded-2xl px-2 py-1 text-sm font-medium",
											selectedLabel === label &&
												"ring-2 ring-primary ring-offset-1",
										)}
									>
										{label}
									</Badge>
								</button>
							))}
							{availableLabels.length === 0 && !showValidation && (
								<span className="text-sm text-muted-foreground">
									Όλες οι επιλογές έχουν τοποθετηθεί
								</span>
							)}
						</div>
					</div>

					{selectedLabel && !showValidation && (
						<p className="text-sm text-muted-foreground">
							Επιλέξατε: <strong>{selectedLabel}</strong> — πατήστε σε μια
							περιοχή του χάρτη
						</p>
					)}

					{/* Interactive map */}
					<GreeceMap
						level={item.level}
						regionLabels={dropRegionLabels}
						activeRegionIds={selectedLabel ? activeRegionIds : undefined}
						validationMap={showValidation ? dropValidationMap : undefined}
						disabled={showValidation}
						onRegionClick={handleRegionClick}
					/>

					{isDropComplete && showValidationButton && (
						<ValidationButton
							showValidation={showValidation}
							onValidate={() => setShowValidation(true)}
						/>
					)}
				</>
			) : (
				<>
					{/* Interactive map — click any region to type your answer */}
					<GreeceMap
						level={item.level}
						regionLabels={typeRegionLabels}
						validationMap={showValidation ? typeValidationMap : undefined}
						disabled={showValidation}
						onRegionClick={handleTypeRegionClick}
					/>

					{/* Input for the selected region */}
					{selectedTypeRegion && !showValidation && (
						<div className="flex items-center gap-2">
							<Input
								type="text"
								autoFocus
								placeholder="Πληκτρολογήστε την απάντησή σας…"
								value={typeAnswers.get(selectedTypeRegion) ?? ""}
								onChange={(e) =>
									updateTypeAnswer(selectedTypeRegion, e.target.value)
								}
							/>
							<RemoveAnswerButton
								onClick={() => clearTypeAnswer(selectedTypeRegion)}
							/>
						</div>
					)}

					{!selectedTypeRegion && !showValidation && (
						<p className="text-sm text-muted-foreground">
							Πατήστε σε οποιαδήποτε περιοχή του χάρτη για να πληκτρολογήσετε
							την απάντησή σας
						</p>
					)}

					{hasAtLeastOneAnswer && showValidationButton && (
						<ValidationButton
							showValidation={showValidation}
							onValidate={() => setShowValidation(true)}
						/>
					)}
				</>
			)}
		</QuizCard>
	)
}
