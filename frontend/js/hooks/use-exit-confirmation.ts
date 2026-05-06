import { router } from "@inertiajs/react"
import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Hook that prevents accidental navigation away from an active session.
 * - Intercepts browser tab close / refresh via `beforeunload`.
 * - Intercepts Inertia navigations and shows a confirmation dialog.
 *
 * Returns state and handlers to wire up an `ExitConfirmDialog` component.
 */
export function useExitConfirmation(active: boolean) {
	const [pendingVisit, setPendingVisit] = useState<{ url: string } | null>(null)
	const removeListenerRef = useRef<(() => void) | null>(null)

	// Browser beforeunload
	useEffect(() => {
		if (!active) {
			return
		}
		const handler = (e: BeforeUnloadEvent) => {
			e.preventDefault()
		}
		window.addEventListener("beforeunload", handler)
		return () => window.removeEventListener("beforeunload", handler)
	}, [active])

	// Inertia navigation intercept
	useEffect(() => {
		if (!active) {
			return
		}

		const remove = router.on("before", (event) => {
			// Allow if user already confirmed
			if (removeListenerRef.current === null) {
				return true
			}
			setPendingVisit({ url: (event.detail.visit as { url: URL }).url.href })
			return false
		})
		removeListenerRef.current = remove
		return () => {
			remove()
			removeListenerRef.current = null
		}
	}, [active])

	const handleConfirm = useCallback(() => {
		const url = pendingVisit?.url
		setPendingVisit(null)
		// Temporarily remove the listener so navigation goes through
		if (removeListenerRef.current) {
			removeListenerRef.current()
			removeListenerRef.current = null
		}
		if (url) {
			router.get(url)
		}
	}, [pendingVisit])

	const handleCancel = useCallback(() => {
		setPendingVisit(null)
	}, [])

	return {
		exitConfirmOpen: !!pendingVisit,
		exitConfirmCancel: handleCancel,
		exitConfirmConfirm: handleConfirm,
	}
}
