import { Button } from "@/components/ui/button"

type ResultsBannerProps = {
	earnedPoints: number
	maxPoints: number
	buttonLabel: string
	onReset: () => void
}

export function ResultsBanner({
	earnedPoints,
	maxPoints,
	buttonLabel,
	onReset,
}: ResultsBannerProps) {
	return (
		<div className="mx-auto max-w-3xl rounded-2xl bg-white p-2 text-center shadow-sm">
			<h1 className="mb-1 text-2xl font-bold">Αποτελέσματα</h1>
			<p className="mb-1 text-3xl font-bold text-blue-600">
				{earnedPoints} / {maxPoints}
			</p>
			<p className="mb-2 text-sm text-gray-600">
				Δείτε τις σωστές και λάθος απαντήσεις σας παρακάτω.
			</p>
			<Button variant="outline" onClick={onReset}>
				{buttonLabel}
			</Button>
		</div>
	)
}
