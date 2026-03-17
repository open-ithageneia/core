import type {
	Exam
} from "@/types/models"

type PlaygroundProps = {
	exam: Exam
}

export default function Playground({ exam }: PlaygroundProps) {
	return (
		<div className="mx-auto max-w-4xl space-y-12 p-8">
			<h1 className="text-3xl font-bold">Quiz Playground</h1>

			{/* ── True / False Statement ── */}
			<section className="space-y-2">
				<h2 className="text-xl font-semibold">True / False</h2>
				{exam.true_false ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <TrueFalseQuestion quiz={exam.true_false[0]} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(exam.true_false[0], null, 2)}
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
				{exam.multiple_choice ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <MultipleChoiceQuestion quiz={exam.multiple_choice[0]} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(exam.multiple_choice[0], null, 2)}
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
				{exam.drag_and_drop ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <DragAndDropQuestion quiz={exam.drag_and_drop} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(exam.drag_and_drop[0], null, 2)}
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
				{exam.matching ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <MatchingQuestion quiz={exam.matching[0]} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(exam.matching[0], null, 2)}
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
				{exam.fill_in_the_blank ? (
					<div className="rounded-lg border p-4">
						{/* TODO: Replace with <FillInTheBlankQuestion quiz={exam.fill_in_the_blank[0]} /> */}
						<pre className="text-sm text-muted-foreground">
							{JSON.stringify(exam.fill_in_the_blank[0], null, 2)}
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
