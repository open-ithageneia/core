import { Button } from "@/components/ui/button"

type ValidationButtonProps = {
	showValidation: boolean
	onValidate: () => void
	correctAnswersCount?: number
	totalScore?: number
}

export default function ValidationButton({
	showValidation,
	onValidate,
	correctAnswersCount,
	totalScore,
}: ValidationButtonProps) {
	return (
		<div className="flex flex-col items-center justify-center gap-2">
			<Button type="button" onClick={onValidate} disabled={showValidation}>
				{showValidation ? "Οι απαντήσεις ελέγχθηκαν" : "Έλεγχος απαντήσεων"}
			</Button>

			{showValidation &&
				correctAnswersCount !== undefined &&
				totalScore !== undefined && (
					<p className="text-sm text-muted-foreground">
						Score: {correctAnswersCount} / {totalScore}
					</p>
				)}
		</div>
	)
}
