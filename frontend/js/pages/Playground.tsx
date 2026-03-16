import type {
	DragAndDrop,
	FillInTheBlank,
	Matching,
	Statement,
} from "@/types/models"

type PlaygroundProps = {
	quizzes: {
		true_false: Statement | null
		multiple_choice: Statement | null
		fill_in_the_blank: FillInTheBlank | null
		drag_and_drop: DragAndDrop | null
		matching: Matching | null
	}
}

export default function Playground({ quizzes }: PlaygroundProps) {
	return (
		<div className="mx-auto max-w-4xl space-y-12 p-8">
			<h1 className="text-3xl font-bold">Quiz Playground</h1>

			{/* ── True / False Statement ── */}
			<section className="space-y-2">
				<h2 className="text-xl font-semibold">True / False</h2>
				{quizzes.true_false ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <TrueFalseQuestion quiz={quizzes.true_false} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(quizzes.true_false, null, 2)}
						</pre>
					</div>
				) : (
					<p className="text-muted-foreground">
						No true/false questions available.
					</p>
				)}
			</section>

			{/* ── Multiple Choice Statement ── */}
			<section className="space-y-2">
				<h2 className="text-xl font-semibold">Multiple Choice</h2>
				{quizzes.multiple_choice ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <MultipleChoiceQuestion quiz={quizzes.multiple_choice} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(quizzes.multiple_choice, null, 2)}
						</pre>
					</div>
				) : (
					<p className="text-muted-foreground">
						No multiple choice questions available.
					</p>
				)}
			</section>

			{/* ── Drag and Drop ── */}
			<section className="space-y-2">
				<h2 className="text-xl font-semibold">Drag and Drop</h2>
				{quizzes.drag_and_drop ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <DragAndDropQuestion quiz={quizzes.drag_and_drop} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(quizzes.drag_and_drop, null, 2)}
						</pre>
					</div>
				) : (
					<p className="text-muted-foreground">
						No drag and drop questions available.
					</p>
				)}
			</section>

			{/* ── Matching ── */}
			<section className="space-y-2">
				<h2 className="text-xl font-semibold">Matching</h2>
				{quizzes.matching ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <MatchingQuestion quiz={quizzes.matching} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(quizzes.matching, null, 2)}
						</pre>
					</div>
				) : (
					<p className="text-muted-foreground">
						No matching questions available.
					</p>
				)}
			</section>

			{/* ── Fill in the Blank ── */}
			<section className="space-y-2">
				<h2 className="text-xl font-semibold">Fill in the Blank</h2>
				{quizzes.fill_in_the_blank ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <FillInTheBlankQuestion quiz={quizzes.fill_in_the_blank} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(quizzes.fill_in_the_blank, null, 2)}
						</pre>
					</div>
				) : (
					<p className="text-muted-foreground">
						No fill in the blank questions available.
					</p>
				)}
			</section>
		</div>
	)
}

