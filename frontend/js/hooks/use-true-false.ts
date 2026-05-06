import { useCallback, useMemo, useState } from "react"
import { useValidation } from "@/hooks/use-validation"
import type { StatementModel } from "@/types/models"

type UseTrueFalseOptions = {
	forceValidation?: boolean
}

export function useTrueFalse(
	item: StatementModel,
	options?: UseTrueFalseOptions,
) {
	const choices = item.content.choices
	const [answers, setAnswers] = useState<(boolean | null)[]>(() =>
		choices.map(() => null),
	)
	const { showValidation, setShowValidation, showValidationButton } =
		useValidation(options)

	const allAnswered = answers.every((a) => a !== null)

	const selectAnswer = useCallback(
		(index: number, value: boolean) => {
			if (showValidation) {
				return
			}
			setAnswers((prev) => {
				const next = [...prev]
				next[index] = value
				return next
			})
		},
		[showValidation],
	)

	const results = useMemo(() => {
		if (!showValidation) {
			return choices.map(() => null)
		}
		return choices.map((choice, i) => answers[i] === choice.is_correct)
	}, [showValidation, choices, answers])

	const correctAnswersCount = useMemo(() => {
		if (!showValidation) {
			return 0
		}
		return results.filter((r) => r === true).length
	}, [showValidation, results])

	return {
		choices,
		answers,
		showValidation,
		setShowValidation,
		showValidationButton,
		allAnswered,
		selectAnswer,
		results,
		correctAnswersCount,
	}
}
