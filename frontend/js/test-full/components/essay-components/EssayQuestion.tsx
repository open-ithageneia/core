import { Textarea } from "@/components/ui/textarea"

type Props = {
	instructions: string
	question: string
	minWords: number
	maxWords: number
	value: string
	onChange: (value: string) => void
}

const EssayQuestion = ({
	instructions,
	question,
	minWords,
	maxWords,
	value,
	onChange,
}: Props) => {
	const wordCount = value
		.trim()
		.replace(/\n/g, " ")
		.split(/\s+/)
		.filter(Boolean).length

	const isOutOfRange = wordCount < minWords || wordCount > maxWords

	return (
		<div className="space-y-6">
			<h2 className="text-xl font-bold">Μέρος Γ</h2>

			<p className="font-semibold">{instructions}</p>

			<p className="text-justify">{question}</p>

			<Textarea
				value={value}
				onChange={(e) => onChange(e.target.value)}
				placeholder="Γράψτε εδώ το κείμενό σας..."
				className="
          min-h-50
          border-2
          border-black
          rounded-none
          resize-none
          focus-visible:ring-0
        "
			/>

			<div className="flex justify-between text-sm">
				<span>Λέξεις: {wordCount}</span>

				<span
					className={
						isOutOfRange
							? "text-destructive font-medium"
							: "text-primary font-medium"
					}
				>
					Όριο: {minWords} – {maxWords}
				</span>
			</div>
		</div>
	)
}

export default EssayQuestion
