import { Button } from "@/components/ui/button"

type ValidationButtonProps = {
	showValidation: boolean
	onValidate: () => void
}

export default function ValidationButton({
	showValidation,
	onValidate,
}: ValidationButtonProps) {
	return (
		<div className="flex flex-col items-center justify-center gap-2">
			<Button type="button" onClick={onValidate} disabled={showValidation}>
				{showValidation ? "Οι απαντήσεις ελέγχθηκαν" : "Έλεγχος απαντήσεων"}
			</Button>
		</div>
	)
}
