import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface ExitConfirmDialogProps {
	open: boolean
	onCancel: () => void
	onConfirm: () => void
}

export function ExitConfirmDialog({
	open,
	onCancel,
	onConfirm,
}: ExitConfirmDialogProps) {
	return (
		<AlertDialog open={open} onOpenChange={(o) => !o && onCancel()}>
			<AlertDialogContent>
				<AlertDialogHeader>
					<AlertDialogTitle>Έξοδος από την εξέταση;</AlertDialogTitle>
					<AlertDialogDescription>
						Αν φύγετε τώρα, η πρόοδός σας θα χαθεί. Είστε σίγουροι;
					</AlertDialogDescription>
				</AlertDialogHeader>
				<AlertDialogFooter>
					<AlertDialogCancel>Ακύρωση</AlertDialogCancel>
					<AlertDialogAction onClick={onConfirm}>Έξοδος</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	)
}
