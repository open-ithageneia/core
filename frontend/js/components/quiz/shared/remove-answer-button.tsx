import { Button } from "@/components/ui/button"

type RemoveAnswerButtonProps = {
	onClick: () => void
}

export default function RemoveAnswerButton({
	onClick,
}: RemoveAnswerButtonProps) {
	return (
		<Button
			type="button"
			variant="ghost"
			size="icon"
			onClick={onClick}
			aria-label="Αφαίρεση απάντησης"
		>
			✕
		</Button>
	)
}
