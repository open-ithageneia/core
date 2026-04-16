import { useMemo, useState } from "react"
import { useValuePool } from "@/lib/utils"
import { ValidationStatus } from "@/types/enums"
import type { DragAndDropModel } from "@/types/models"
import type { CellValue, ValidationState } from "@/types/quiz"

export function useDragAndDrop(item: DragAndDropModel) {
	const allValues = useMemo(
		() => item.content.flatMap((group) => group.values),
		[item],
	)

	const { availableValues, removeValueFromAvailable, returnValueToAvailable } =
		useValuePool(allValues)

	const [showValidation, setShowValidation] = useState(false)

	const maxRows = Math.max(...item.content.map((group) => group.values.length))
	const columnCount = item.content.length
	const totalScore = maxRows * columnCount

	const [tableValues, setTableValues] = useState<CellValue[][]>(
		Array.from({ length: maxRows }, () =>
			Array.from({ length: columnCount }, () => null),
		),
	)

	function placeValueInCell(rowIndex: number, colIndex: number, value: string) {
		if (showValidation) return
		if (tableValues[rowIndex][colIndex]) return

		setTableValues((prevTableValues) => {
			const newTableValues = prevTableValues.map((row) => [...row])
			newTableValues[rowIndex][colIndex] = value
			return newTableValues
		})

		removeValueFromAvailable(value)
	}

	function clearCell(rowIndex: number, colIndex: number) {
		if (showValidation) return

		const value = tableValues[rowIndex][colIndex]
		if (!value) return

		setTableValues((prevTableValues) => {
			const newTableValues = prevTableValues.map((row) => [...row])
			newTableValues[rowIndex][colIndex] = null
			return newTableValues
		})

		returnValueToAvailable(value)
	}

	function isValueCorrectForColumn(colIndex: number, value: string | null) {
		if (!value) return false
		return item.content[colIndex].values.includes(value)
	}

	function getCellValidationState(
		rowIndex: number,
		colIndex: number,
	): ValidationState {
		const cellValue = tableValues[rowIndex][colIndex]
		if (!showValidation || !cellValue) return null
		return isValueCorrectForColumn(colIndex, cellValue)
			? ValidationStatus.Correct
			: ValidationStatus.Incorrect
	}

	const isTableComplete = useMemo(() => {
		return tableValues.every((row) => row.every((cell) => cell !== null))
	}, [tableValues])

	const correctAnswersCount = useMemo(() => {
		return tableValues.reduce((count, row) => {
			return (
				count +
				row.filter((cellValue, colIndex) =>
					cellValue ? item.content[colIndex].values.includes(cellValue) : false,
				).length
			)
		}, 0)
	}, [tableValues, item])

	function handleDragEnd(sourceValue: string, targetId: string) {
		if (showValidation) return
		if (!targetId.startsWith("cell-")) return

		const [, rowIndexString, colIndexString] = targetId.split("-")
		const rowIndex = Number(rowIndexString)
		const colIndex = Number(colIndexString)

		if (tableValues[rowIndex][colIndex]) return

		placeValueInCell(rowIndex, colIndex, sourceValue)
	}

	return {
		availableValues,
		showValidation,
		setShowValidation,
		maxRows,
		tableValues,
		totalScore,
		isTableComplete,
		correctAnswersCount,
		clearCell,
		getCellValidationState,
		handleDragEnd,
	}
}
