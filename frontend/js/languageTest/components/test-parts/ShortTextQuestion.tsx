// component για short text (συμπλήρωση κενού)

import { Input } from "@/components/ui/input"

type Props = {
	question: {
		id: string
		prompt?: string
		question: string
	}
	value: string | undefined
	onChange: (value: string) => void
}

const ShortTextQuestion = ({ question, value, onChange }: Props) => {
	const renderQuestionText = () => {
		const parts = question.question.split("__")

		if (parts.length < 2) return question.question

		return (
			<>
				{parts[0]}
				<Input
					value={value || ""}
					onChange={(e) => onChange(e.target.value)}
					className="
            inline-block
            w-40
            mx-2
            border-0
            border-b-2
            border-black
            rounded-none
            px-1
            focus-visible:ring-0
            focus-visible:ring-offset-0
            focus-visible:border-black
            bg-transparent
            font-semibold
          "
				/>
				{parts[1]}
			</>
		)
	}

	return (
		<div className="space-y-2">
			{question.prompt && (
				<p className="text-muted-foreground">{question.prompt}</p>
			)}

			<p className="font-medium leading-6">{renderQuestionText()}</p>
		</div>
	)
}

export default ShortTextQuestion
