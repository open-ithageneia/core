import { usePage } from "@inertiajs/react"

export function useNav() {
	return usePage().props.nav
}
