import { useCallback, useMemo, useState } from "react"
import { useValidation } from "@/hooks/use-validation"
import { normalizeForTextComparison, useValuePool } from "@/lib/utils"
import { ValidationStatus } from "@/types/enums"
import type { FillInTheBlankModel } from "@/types/models"
import type { ValidationState } from "@/types/quiz"

type UseFillInTheBlankOptions = {
	forceValidation?: boolean
}

export function useFillInTheBlank(
	item: FillInTheBlankModel,
	options?: UseFillInTheBlankOptions,
) {
	const { showValidation, setShowValidation, showValidationButton } =
		useValidation(options)

	const content = item.content

	// Build a flat list of blanks with their correct answers
	const blanks = useMemo(() => {
		const result: {
			textIndex: number
			partIndex: number
			choices: { text: string; is_correct: boolean }[]
		}[] = []
		for (let ti = 0; ti < content.texts.length; ti++) {
			for (let pi = 0; pi < content.texts[ti].parts.length; pi++) {
				const part = content.texts[ti].parts[pi]
				if (part.is_blank && part.choices) {
					result.push({
						textIndex: ti,
						partIndex: pi,
						choices: part.choices,
					})
				}
			}
		}
		return result
	}, [content.texts])

	// Determine fill-in-the-blank variant:
	// 1. "choices_shown" — prompt_instruction_choices is provided (drag & drop word bank)
	// 2. "inline_choices" — has_multiple_choices is true (each blank has its own dropdown)
	// 3. "hidden" — no choices shown at all, user must type (normalized comparison)
	const variant = useMemo(() => {
		if (content.has_multiple_choices) {
			return "inline_choices" as const
		}
		if (
			content.prompt_instruction_choices &&
			content.prompt_instruction_choices.length > 0
		) {
			return "choices_shown" as const
		}
		return "hidden" as const
	}, [content.has_multiple_choices, content.prompt_instruction_choices])

	// --- Drag-and-drop state for "choices_shown" variant ---
	const wordBankValues = useMemo(
		() => content.prompt_instruction_choices ?? [],
		[content.prompt_instruction_choices],
	)
	const { availableValues, removeValueFromAvailable, returnValueToAvailable } =
		useValuePool(wordBankValues)

	// For choices_shown: each blank holds a dropped string | null
	const [droppedValues, setDroppedValues] = useState<(string | null)[]>(() =>
		blanks.map(() => null),
	)

	const dropValue = useCallback(
		(blankIndex: number, value: string) => {
			if (showValidation) {
				return
			}
			setDroppedValues((prev) => {
				const next = [...prev]
				next[blankIndex] = value
				return next
			})
			removeValueFromAvailable(value)
		},
		[showValidation, removeValueFromAvailable],
	)

	const clearDroppedValue = useCallback(
		(blankIndex: number) => {
			if (showValidation) {
				return
			}
			const val = droppedValues[blankIndex]
			if (!val) {
				return
			}
			setDroppedValues((prev) => {
				const next = [...prev]
				next[blankIndex] = null
				return next
			})
			returnValueToAvailable(val)
		},
		[showValidation, droppedValues, returnValueToAvailable],
	)

	function handleDragEnd(sourceValue: string, targetId: string) {
		if (showValidation) {
			return
		}
		if (!targetId.startsWith("blank-")) {
			return
		}
		const blankIndex = Number(targetId.replace("blank-", ""))
		if (droppedValues[blankIndex] !== null) {
			return
		}
		dropValue(blankIndex, sourceValue)
	}

	// --- Text input state for "hidden" and "inline_choices" variants ---
	const [textAnswers, setTextAnswers] = useState<string[]>(() =>
		blanks.map(() => ""),
	)

	const updateAnswer = useCallback(
		(blankIndex: number, value: string) => {
			if (showValidation) {
				return
			}
			setTextAnswers((prev) => {
				const next = [...prev]
				next[blankIndex] = value
				return next
			})
		},
		[showValidation],
	)

	// --- Unified answers (for display / validation) ---
	const answers = useMemo(() => {
		if (variant === "choices_shown") {
			return droppedValues.map((v) => v ?? "")
		}
		return textAnswers
	}, [variant, droppedValues, textAnswers])

	const hasAtLeastOneAnswer =
		variant === "choices_shown"
			? droppedValues.some((v) => v !== null)
			: textAnswers.some((a) => a.trim() !== "")

	const allBlanksFilledDnd =
		variant === "choices_shown" ? droppedValues.every((v) => v !== null) : false

	// --- Validation ---
	const states: ValidationState[] = useMemo(() => {
		if (!showValidation) {
			return blanks.map(() => null)
		}
		return blanks.map((blank, i) => {
			const userAnswer = answers[i]
			if (variant === "hidden") {
				const normalizedUser = normalizeForTextComparison(userAnswer)
				const isCorrect = blank.choices.some(
					(c) =>
						c.is_correct &&
						normalizeForTextComparison(c.text) === normalizedUser,
				)
				return isCorrect ? ValidationStatus.Correct : ValidationStatus.Incorrect
			}
			const trimmed = userAnswer.trim().toLowerCase()
			const isCorrect = blank.choices.some(
				(c) => c.is_correct && c.text.trim().toLowerCase() === trimmed,
			)
			return isCorrect ? ValidationStatus.Correct : ValidationStatus.Incorrect
		})
	}, [showValidation, blanks, answers, variant])

	const correctAnswersCount = useMemo(
		() => states.filter((s) => s === ValidationStatus.Correct).length,
		[states],
	)

	return {
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
		// DnD-specific
		availableValues,
		droppedValues,
		clearDroppedValue,
		handleDragEnd,
	}
}
