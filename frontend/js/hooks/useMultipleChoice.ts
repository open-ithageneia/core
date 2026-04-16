import { useCallback, useMemo, useState } from "react"
import { ValidationStatus } from "@/types/enums"
import type { StatementModel } from "@/types/models"
import type { ValidationState } from "@/types/quiz"

export function useMultipleChoice(item: StatementModel) {
	const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
	const [showValidation, setShowValidation] = useState(false)

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
		hasSelection,
		selectChoice,
		choiceStates,
		correctAnswersCount,
		choices,
	}
}
