type PostValidationNotesProps = {
	title: string
	notes: string[]
}

export default function PostValidationNotes({
	title,
	notes,
}: PostValidationNotesProps) {
	if (notes.length === 0) {
		return null
	}

	return (
		<div className="rounded-lg border border-amber-300 bg-amber-50 p-3 dark:border-amber-700 dark:bg-amber-950">
			<p className="mb-1 text-sm font-medium text-amber-800 dark:text-amber-300">
				{title}
			</p>
			<ul className="grid grid-cols-[repeat(auto-fill,minmax(10rem,1fr))] gap-x-4 list-inside list-disc text-sm text-amber-700 dark:text-amber-400">
				{notes.map((text) => (
					<li key={text}>{text}</li>
				))}
			</ul>
		</div>
	)
}
