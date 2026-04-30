import { useCallback, useMemo, useState } from "react"
import { useValidation } from "@/hooks/useValidation"
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
	const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
	const { showValidation, setShowValidation, showValidationButton } =
		useValidation(options)

	const choices = item.content.choices

	const hasSelection = selectedIndex !== null

	const selectChoice = useCallback(
		(index: number) => {
			if (showValidation) return
			setSelectedIndex(index)
		},
		[showValidation],
	)

	const choiceStates: ValidationState[] = useMemo(() => {
		if (!showValidation) return choices.map(() => null)
		return choices.map((choice, index) => {
			if (choice.is_correct) return ValidationStatus.Correct
			if (index === selectedIndex) return ValidationStatus.Incorrect
			return null
		})
	}, [showValidation, choices, selectedIndex])

	const isCorrect = useMemo(() => {
		if (!showValidation || selectedIndex === null) return false
		return choices[selectedIndex].is_correct
	}, [showValidation, selectedIndex, choices])

	const correctAnswersCount = isCorrect ? 1 : 0

	return {
		selectedIndex,
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
