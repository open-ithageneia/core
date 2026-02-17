import type { FullWordMatchingQuestion } from "../types/Full.types"
import QuestionMediaBlock from "./QuestionMediaBlock"

type Props = {
	question: FullWordMatchingQuestion
	value: Record<string, string> | undefined
	onChange: (value: Record<string, string>) => void
}

const WordMatchingQuestion = ({ question, value = {}, onChange }: Props) => {
	const handleSelect = (blankKey: string, selected: string) => {
		onChange({
			...value,
			[blankKey]: selected,
		})
	}

	const renderText = () => {
		const parts = question.textTemplate.split(/(\d+\.\s__)/g)

		return parts.map((part) => {
			const match = part.match(/^(\d+)\.\s__$/)

			if (!match) return <span key={part}>{part}</span>

			const blankKey = match[1]

			return (
				<span key={blankKey} className="mx-1">
					<select
						value={value[blankKey] || ""}
						onChange={(e) => handleSelect(blankKey, e.target.value)}
						className="border rounded px-2 py-1"
					>
						<option value="">--</option>
						{Object.entries(question.wordBank).map(([k, label]) => (
							<option key={k} value={k}>
								{k}. {label}
							</option>
						))}
					</select>
				</span>
			)
		})
	}

	return (
		<div className="space-y-4">
			<p className="font-medium">{question.question}</p>

			{question.media && question.media.length > 0 && (
				<QuestionMediaBlock media={question.media} />
			)}

			<div className="leading-8">{renderText()}</div>
		</div>
	)
}

export default WordMatchingQuestion
