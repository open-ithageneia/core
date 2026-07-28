import { useCallback, useMemo, useState } from "react"
import { useValidation } from "@/hooks/quiz/use-validation"
import { ValidationStatus } from "@/types/enums"
import type { StatementModel } from "@/types/models"
import type { ValidationState } from "@/types/quiz"

type UseMultipleChoiceOptions = {
	forceValidation?: boolean
}

export function useMultipleChoice(
	item: StatementModel,
	options?: UseMultipleChoiceOptions,
) {
	const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set())
	const { showValidation, setShowValidation, showValidationButton } =
		useValidation(options)

	const choices = item.content.choices

	const totalCorrect = useMemo(
		() => choices.filter((c) => c.is_correct).length,
		[choices],
	)
	const isMultiSelect = totalCorrect > 1

	const hasSelection = selectedIndices.size > 0

	const selectChoice = useCallback(
		(index: number) => {
			if (showValidation) {
				return
			}
			setSelectedIndices((prev) => {
				if (isMultiSelect) {
					const next = new Set(prev)
					if (next.has(index)) {
						next.delete(index)
					} else {
						next.add(index)
					}
					return next
				}
				return new Set([index])
			})
		},
		[showValidation, isMultiSelect],
	)

	const choiceStates: ValidationState[] = useMemo(() => {
		if (!showValidation) {
			return choices.map(() => null)
		}
		return choices.map((choice, index) => {
			if (choice.is_correct) {
				return ValidationStatus.Correct
			}
			if (selectedIndices.has(index)) {
				return ValidationStatus.Incorrect
			}
			return null
		})
	}, [showValidation, choices, selectedIndices])

	// A multiple-choice question is a single scoring unit however many options it
	// has — the whole question is worth one sub-answer. (A true/false block is the
	// opposite: each of its statements is scored on its own.)
	const subAnswersCount = 1

	const correctAnswersCount = useMemo(() => {
		if (!showValidation) {
			return 0
		}
		// All or nothing: every correct option selected and no incorrect one. For
		// single-select that reduces to "picked the one correct choice".
		const isFullyCorrect = choices.every(
			(choice, index) => selectedIndices.has(index) === choice.is_correct,
		)
		return isFullyCorrect ? 1 : 0
	}, [showValidation, choices, selectedIndices])

	return {
		totalCorrect,
		subAnswersCount,
		selectedIndices,
		isMultiSelect,
		showValidation,
		setShowValidation,
		showValidationButton,
		hasSelection,
		selectChoice,
		choiceStates,
		correctAnswersCount,
		choices,
	}
}
