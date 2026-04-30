import { useState } from "react"

type UseValidationOptions = {
	forceValidation?: boolean
}

/**
 * Shared validation state for quiz components.
 *
 * - `forceValidation === undefined` → standalone mode (internal toggle, show button)
 * - `forceValidation === false` → training in-progress (no validation yet, hide button)
 * - `forceValidation === true` → training finished (force show results, hide button)
 */
export function useValidation(options?: UseValidationOptions) {
	const [internalValidation, setInternalValidation] = useState(false)

	const isControlled = options?.forceValidation !== undefined
	const showValidation = isControlled
		? Boolean(options.forceValidation)
		: internalValidation
	const setShowValidation = setInternalValidation
	const showValidationButton = !isControlled

	return { showValidation, setShowValidation, showValidationButton }
}
