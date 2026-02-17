// frontend\src\test-full\pages\TestFullQuestion.tsx

import CategorizationQuestionComponent from "../components/CategorizationQuestionComponent"
import ListInputQuestion from "../components/ListInputQuestion"
import MapPointsQuestion from "../components/MapPointsQuestion"
import MatchingQuestionComponent from "../components/MatchingQuestion"
import MultipleChoiceQuestion from "../components/MultipleChoiceQuestion"
import MultiSelectQuestion from "../components/MultiSelectQuestion"
import OpenTextQuestion from "../components/OpenTextQuestion"
import ShortTextQuestion from "../components/ShortTextQuestion"
import TrueFalseGroupQuestion from "../components/TrueFalseGroupQuestion"
import WordMatchingQuestion from "../components/WordMatchingQuestion"
import type { FullAnswer, FullQuestion, MapPoint } from "../types/Full.types"

type Props = {
	question: FullQuestion
	value?: FullAnswer
	onChange: (id: string, value: FullAnswer) => void
}

const GeographyFullQuestion = ({ question, value, onChange }: Props) => {
	return (
		<div className="space-y-4 border p-4 rounded">
			{question.type === "multipleChoice" && (
				<MultipleChoiceQuestion
					question={question}
					value={value as string}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "shortText" && (
				<ShortTextQuestion
					question={question}
					value={value}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "matching" && (
				<MatchingQuestionComponent
					question={question}
					value={
						value && typeof value === "object" && !Array.isArray(value)
							? value
							: {}
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "multiSelect" && (
				<MultiSelectQuestion
					question={question}
					value={
						question.type === "multiSelect" && Array.isArray(value)
							? (value as string[])
							: []
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "listInput" && (
				<ListInputQuestion
					question={question}
					value={
						question.type === "listInput" && Array.isArray(value)
							? (value as string[])
							: []
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "trueFalseGroup" && (
				<TrueFalseGroupQuestion
					question={question}
					value={
						value && typeof value === "object" && !Array.isArray(value)
							? (value as Record<string, "T" | "F">)
							: {}
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "categorization" && (
				<CategorizationQuestionComponent
					question={question}
					value={
						value && typeof value === "object" && !Array.isArray(value)
							? value
							: {}
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "mapPoints" && (
				<MapPointsQuestion
					question={question}
					value={
						question.type === "mapPoints"
							? (value as MapPoint[] | undefined)
							: undefined
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "wordMatching" && (
				<WordMatchingQuestion
					question={question}
					value={
						value && typeof value === "object" && !Array.isArray(value)
							? (value as Record<string, string>)
							: {}
					}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}

			{question.type === "openText" && (
				<OpenTextQuestion
					question={question}
					value={typeof value === "string" ? value : ""}
					onChange={(val) => onChange(question.id, val)}
				/>
			)}
		</div>
	)
}

export default GeographyFullQuestion
