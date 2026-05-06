import { useCallback, useMemo, useState } from "react"
import { useValidation } from "@/hooks/quiz/use-validation"
import { normalizeForTextComparison } from "@/lib/utils"
import { ValidationStatus } from "@/types/enums"
import type { OpenEndedModel } from "@/types/models"
import type { ValidationState } from "@/types/quiz"

/**
 * Match each user answer against the correct answer groups using simple normalization.
 * Each answer group (list of alternatives) can only be matched once.
 * A user answer is correct if it matches any alternative in an unmatched group.
 * Returns a validation state per user answer and the set of matched group indices.
 */
function validateAnswers(
	userAnswers: string[],
	correctAnswerGroups: string[][],
): { states: ValidationState[]; matchedGroupIndices: Set<number> } {
	const matchedGroupIndices = new Set<number>()
	const states: ValidationState[] = userAnswers.map((answer) => {
		const norm = normalizeForTextComparison(answer)
		if (norm.length === 0) {
			return ValidationStatus.Incorrect
		}
		for (let i = 0; i < correctAnswerGroups.length; i++) {
			if (matchedGroupIndices.has(i)) {
				continue
			}
			const alternatives = correctAnswerGroups[i]
			if (
				alternatives.some((alt) => normalizeForTextComparison(alt) === norm)
			) {
				matchedGroupIndices.add(i)
				return ValidationStatus.Correct
			}
		}
		return ValidationStatus.Incorrect
	})
	return { states, matchedGroupIndices }
}

type UseOpenEndedOptions = {
	forceValidation?: boolean
}

export function useOpenEnded(
	item: OpenEndedModel,
	options?: UseOpenEndedOptions,
) {
	const [answers, setAnswers] = useState<string[]>([""])
	const { showValidation, setShowValidation, showValidationButton } =
		useValidation(options)

	const hasAtLeastOneAnswer = useMemo(
		() => answers.some((a) => a.trim().length > 0),
		[answers],
	)

	const { states, matchedGroupIndices } = useMemo(() => {
		if (!showValidation) {
			return {
				states: [] as ValidationState[],
				matchedGroupIndices: new Set<number>(),
			}
		}
		return validateAnswers(answers, item.content.texts)
	}, [showValidation, answers, item.content.texts])

	const correctAnswersCount = useMemo(
		() => states.filter((s) => s === ValidationStatus.Correct).length,
		[states],
	)

	const missedAnswers = useMemo(() => {
		if (!showValidation) {
			return []
		}
		return item.content.texts
			.filter((_, i) => !matchedGroupIndices.has(i))
			.map((alts) => alts[0])
	}, [showValidation, item.content.texts, matchedGroupIndices])

	const addAnswerField = useCallback(() => {
		if (showValidation) {
			return
		}
		setAnswers((prev) => [...prev, ""])
	}, [showValidation])

	const removeAnswerField = useCallback(
		(index: number) => {
			if (showValidation) {
				return
			}
			setAnswers((prev) => prev.filter((_, i) => i !== index))
		},
		[showValidation],
	)

	const updateAnswer = useCallback(
		(index: number, value: string) => {
			if (showValidation) {
				return
			}
			setAnswers((prev) => {
				const updated = [...prev]
				updated[index] = value
				return updated
			})
		},
		[showValidation],
	)

	const canAddAnswer = !showValidation

	return {
		answers,
		showValidation,
		setShowValidation,
		showValidationButton,
		hasAtLeastOneAnswer,
		states,
		correctAnswersCount,
		missedAnswers,
		canAddAnswer,
		addAnswerField,
		removeAnswerField,
		updateAnswer,
		minCorrectAnswers: item.content.min_correct_answers,
	}
}
