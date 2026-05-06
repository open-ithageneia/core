import { Button } from "@/components/ui/button"

type AddAnswerButtonProps = {
	onClick: () => void
}

export default function AddAnswerButton({ onClick }: AddAnswerButtonProps) {
	return (
		<Button type="button" variant="outline" size="sm" onClick={onClick}>
			+ Προσθήκη απάντησης
		</Button>
	)
}
