import { useCallback, useMemo, useState } from "react"
import { useValidation } from "@/hooks/quiz/use-validation"
import { useValuePool } from "@/lib/utils"
import { ValidationStatus } from "@/types/enums"
import type { MatchingItem, MatchingModel } from "@/types/models"
import type { CellValue, ValidationState } from "@/types/quiz"

type UseMatchingOptions = {
	forceValidation?: boolean
}

export function useMatching(item: MatchingModel, options?: UseMatchingOptions) {
	const allValues = useMemo(
		() => item.content[1].items, // use only 2nd column values
		[item],
	)

	const { availableValues, removeValueFromAvailable, returnValueToAvailable } =
		useValuePool(allValues)

	const { showValidation, setShowValidation, showValidationButton } =
		useValidation(options)

	const maxRows = Math.max(...item.content.map((group) => group.items.length))
	const columnCount = item.content.length
	const totalScore = maxRows * columnCount

	const [tableValues, setTableValues] = useState<CellValue<MatchingItem>[][]>(
		Array.from({ length: maxRows }, (_, rowIndex) =>
			Array.from({ length: columnCount }, (_, colIndex) =>
				colIndex === 0 ? (item.content[0].items[rowIndex] ?? null) : null,
			),
		),
	)

	function placeValueInCell(
		rowIndex: number,
		colIndex: number,
		value: MatchingItem,
	) {
		if (showValidation) {
			return
		}
		if (tableValues[rowIndex][colIndex]) {
			return
		}

		setTableValues((prevTableValues) => {
			const newTableValues = prevTableValues.map((row) => [...row])
			newTableValues[rowIndex][colIndex] = value
			return newTableValues
		})

		removeValueFromAvailable(value)
	}

	function clearCell(rowIndex: number, colIndex: number) {
		if (showValidation) {
			return
		}

		const value = tableValues[rowIndex][colIndex]
		if (!value) {
			return
		}

		setTableValues((prevTableValues) => {
			const newTableValues = prevTableValues.map((row) => [...row])
			newTableValues[rowIndex][colIndex] = null
			return newTableValues
		})

		returnValueToAvailable(value)
	}

	const isValueCorrect = useCallback(
		(leftItem: CellValue<MatchingItem>, rightItem: CellValue<MatchingItem>) => {
			if (!rightItem) {
				return false
			}
			return leftItem?.matched_id === rightItem.id
		},
		[],
	)

	function getCellValidationState(
		rowIndex: number,
		colIndex: number,
	): ValidationState {
		const leftItem = tableValues[rowIndex][0]
		const rightItem = tableValues[rowIndex][1] // the answer
		if (colIndex === 0 || !showValidation) {
			return null
		}

		if (!rightItem) {
			return ValidationStatus.Incorrect
		}

		return isValueCorrect(leftItem, rightItem)
			? ValidationStatus.Correct
			: ValidationStatus.Incorrect
	}

	function getCorrectValue(rowIndex: number): MatchingItem | null {
		if (!showValidation) {
			return null
		}

		const leftItem = tableValues[rowIndex][0]
		const rightItem = tableValues[rowIndex][1]
		if (!leftItem || isValueCorrect(leftItem, rightItem)) {
			return null
		}

		return allValues.find((v) => v.id === leftItem.matched_id) ?? null
	}

	const isTableComplete = useMemo(() => {
		return tableValues.every((row) => row.every((cell) => cell !== null))
	}, [tableValues])

	const correctAnswersCount = useMemo(() => {
		return tableValues.reduce((count, row) => {
			const leftItem = row[0]
			const rightItem = row[1]
			return count + (isValueCorrect(leftItem, rightItem) ? 1 : 0)
		}, 0)
	}, [tableValues, isValueCorrect])

	function handleDragEnd(sourceValue: MatchingItem, targetId: string) {
		if (showValidation) {
			return
		}
		if (!targetId.startsWith("droppableCell-")) {
			return
		}

		const [, rowIndexString, colIndexString] = targetId.split("-")
		const rowIndex = Number(rowIndexString)
		const colIndex = Number(colIndexString)

		if (tableValues[rowIndex][colIndex]) {
			return
		}

		placeValueInCell(rowIndex, colIndex, sourceValue)
	}

	return {
		availableValues,
		showValidation,
		setShowValidation,
		showValidationButton,
		maxRows,
		tableValues,
		totalScore,
		isTableComplete,
		correctAnswersCount,
		clearCell,
		getCellValidationState,
		getCorrectValue,
		handleDragEnd,
	}
}
