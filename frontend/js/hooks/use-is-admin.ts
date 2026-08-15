import { usePage } from "@inertiajs/react"

/** Whether the logged-in user is a staff member, shared on every page. */
export function useIsAdmin() {
	return usePage().props.is_admin
}
