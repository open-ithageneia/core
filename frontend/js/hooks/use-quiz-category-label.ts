import { usePage } from "@inertiajs/react"

/**
 * Names a quiz category in Greek. The names live on the quiz category table and
 * are shared on every page, so a code that is missing from the map (a category
 * added since the page was loaded) falls back to the code itself.
 */
export function useQuizCategoryLabel() {
	const labels = usePage().props.quiz_category_labels
	return (code: string) => labels[code] ?? code
}
