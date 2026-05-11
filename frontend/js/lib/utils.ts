import { type ClassValue, clsx } from "clsx"
import { useMemo, useState } from "react"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs))
}

export function shuffleArray<T>(array: T[]): T[] {
	const newArray = [...array]

	for (let i = newArray.length - 1; i > 0; i--) {
		const j = Math.floor(Math.random() * (i + 1))
		;[newArray[i], newArray[j]] = [newArray[j], newArray[i]]
	}

	return newArray
}

export function useValuePool<T>(values: T[]) {
	const initialValues = useMemo(() => shuffleArray(values), [values])

	const [availableValues, setAvailableValues] = useState<T[]>(initialValues)

	function returnValueToAvailable(value: T) {
		setAvailableValues((prev) => [...prev, value])
	}

	function removeValueFromAvailable(value: T) {
		setAvailableValues((prev) => {
			const idx = prev.indexOf(value)
			if (idx === -1) {
				return prev
			}
			return [...prev.slice(0, idx), ...prev.slice(idx + 1)]
		})
	}

	return {
		availableValues,
		returnValueToAvailable,
		removeValueFromAvailable,
	}
}

export function normalizeForTextComparison(s: string): string {
	let text = s

	// Strip combining diacritical marks (accents/tonos/dialytika)
	text = text.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
	text = text.normalize("NFC")

	// Lowercase & whitespace collapse
	text = text.trim().toLowerCase().replace(/\s+/g, " ")

	// Strip punctuation (keeps letters, numbers, and spaces)
	text = text.replace(/[^\p{L}\p{N}\s]/gu, "")

	// Final sigma → regular sigma
	text = text.replace(/ς/g, "σ")

	// Phonetically identical vowel digraphs (must come before single-char replacements)
	text = text.replace(/αι/g, "ε")
	text = text.replace(/ει/g, "ι")
	text = text.replace(/οι/g, "ι")
	text = text.replace(/υι/g, "ι")

	// Single-char vowel merges
	text = text.replace(/η/g, "ι")
	text = text.replace(/υ/g, "ι")
	text = text.replace(/ω/g, "ο")

	// Collapse double consonants (e.g. λλ→λ, σσ→σ, ρρ→ρ)
	text = text.replace(/(.)\1+/g, "$1")

	return text
}
