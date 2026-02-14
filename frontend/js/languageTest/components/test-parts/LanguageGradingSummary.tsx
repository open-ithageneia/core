import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import type { GradedAnswer } from "../../types/language.types"

type Props = {
	gradedAnswers: GradedAnswer[]
}

const LanguageGradingSummary = ({ gradedAnswers }: Props) => {
	const total = gradedAnswers.length
	const correctCount = gradedAnswers.filter((a) => a.correct).length

	return (
		<Card className="mt-4">
			<CardContent>
				<h3 className="mb-2 text-lg font-semibold">Αξιολόγηση</h3>

				<div className="mb-3">
					<Badge className="bg-primary text-primary-foreground">
						Σωστά: {correctCount} / {total}
					</Badge>
				</div>

				<ul className="space-y-2">
					{gradedAnswers.map((a, i) => (
						<li key={a.id} className="rounded-md border p-2">
							<p className="text-sm font-medium">
								{i + 1}. {a.userAnswer || "—"} → {a.correctAnswer}
							</p>

							<div className="mt-1 flex gap-2">
								<Badge
									className={
										a.correct
											? "bg-primary text-primary-foreground"
											: "bg-destructive text-white"
									}
								>
									{a.correct ? "σωστό" : "λάθος"}
								</Badge>

								{a.type === "shortText" && (
									<Badge
										className={
											a.correct
												? a.hasSpellingErrors
													? "bg-secondary text-secondary-foreground"
													: "bg-secondary text-secondary-foreground"
												: "bg-destructive text-white"
										}
									>
										{a.correct
											? a.hasSpellingErrors
												? "σωστό με ορθογραφικά"
												: "σωστό λεκτικό"
											: "λάθος λεκτικό"}
									</Badge>
								)}
							</div>
						</li>
					))}
				</ul>
			</CardContent>
		</Card>
	)
}

export default LanguageGradingSummary
