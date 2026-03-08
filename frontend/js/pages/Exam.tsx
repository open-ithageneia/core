import { Head } from "@inertiajs/react"
import {
	Exam,
	Statement,
	FillInTheBlank,
	DragAndDrop,
	Matching
} from "@/types/models"

interface Props {
	exam: Exam
}

export default function ExamSimulation({ exam }: Props) {
	return (
		<>
			<Head title="Exam Simulation" />
			<div className="max-w-2xl mx-auto p-6 space-y-8">
				<h1 className="text-2xl font-bold">Exam Simulation</h1>

				{exam.true_false.map((q: Statement) => (
					<div key={q.id} className="border rounded-lg p-4 space-y-2">
						<span className="text-xs text-gray-400 uppercase">True / False</span>
						<p>{q.content.prompt_text}</p>
					</div>
				))}

				{exam.multiple_choice.map((q: Statement) => (
					<div key={q.id} className="border rounded-lg p-4 space-y-2">
						<span className="text-xs text-gray-400 uppercase">Multiple Choice</span>
						<p>{q.content.prompt_text}</p>
						<ul className="list-disc list-inside text-gray-600">
							{q.content.choices.map((c, i) => (
								<li key={i}>{c.text}</li>
							))}
						</ul>
					</div>
				))}

				{exam.fill_in_the_blank.map((q: FillInTheBlank) => (
					<div key={q.id} className="border rounded-lg p-4 space-y-2">
						<span className="text-xs text-gray-400 uppercase">Fill in the Blank</span>
						{q.content.texts.map((text, i) => (
							<p key={i}>{text}</p>
						))}
					</div>
				))}

				{exam.drag_and_drop.map((q: DragAndDrop) => {
					const [left, right] = q.content
					return (
						<div key={q.id} className="border rounded-lg p-4 space-y-2">
							<span className="text-xs text-gray-400 uppercase">Drag and Drop</span>
							<div className="grid grid-cols-2 gap-2 text-gray-600">
								<span className="font-medium">{left.title}</span>
								<span className="font-medium">{right.title}</span>
								{left.values.map((value, i) => (
									<>
										<span key={`l-${i}`}>{value}</span>
										<span key={`r-${i}`}>{right.values[i]}</span>
									</>
								))}
							</div>
						</div>
					)
				})}

				{exam.matching.map((q: Matching) => {
					const [left, right] = q.content
					return (
						<div key={q.id} className="border rounded-lg p-4 space-y-2">
							<span className="text-xs text-gray-400 uppercase">Matching</span>
							<div className="grid grid-cols-2 gap-2 text-gray-600">
								<span className="font-medium">{left.title}</span>
								<span className="font-medium">{right.title}</span>
								{left.items.map((item, i) => (
									<>
										<span key={`l-${i}`}>{item.text}</span>
										<span key={`r-${i}`}>{right.items[i]?.text}</span>
									</>
								))}
							</div>
						</div>
					)
				})}
			</div>
		</>
	)
}
