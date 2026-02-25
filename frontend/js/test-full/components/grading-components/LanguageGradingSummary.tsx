import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import type { FullGradedAnswer } from "../../types/Full.types"

type Props = {
	gradedAnswers: FullGradedAnswer[]
}

const LanguageGradingSummary = ({ gradedAnswers }: Props) => {
	const total = gradedAnswers.length
	const correctCount = gradedAnswers.filter((a) => a.correct).length

	const renderCorrectAnswer = (a: FullGradedAnswer) => {
		const ca = a.correctAnswer

		if (typeof ca === "string") return ca

		if (Array.isArray(ca)) return ca.join(" ")

		if (typeof ca === "object" && ca !== null) {
			return Object.values(ca).join(", ")
		}

		return ""
	}

	return (
		<Card className="mt-8">
			<CardContent className="space-y-6">
				{/* 🔹 Τελικό αποτέλεσμα */}
				<div className="text-center">
					<p className="text-sm text-muted-foreground">Τελικό αποτέλεσμα</p>
					<p className="text-3xl font-bold">
						{correctCount} / {total}
					</p>
				</div>

				{/* 🔹 Αναλυτικά */}
				<div className="grid md:grid-cols-2 gap-3">
					{gradedAnswers.map((a, i) => (
						<div
							key={a.id}
							className="rounded-md border p-3 space-y-2 bg-muted/20"
						>
							<div className="flex justify-between items-center">
								<span className="text-xs font-medium">Ερ. {i + 1}</span>

								<Badge
									className={
										a.correct
											? "bg-primary text-primary-foreground"
											: "bg-red-500 text-white"
									}
								>
									{a.correct ? "✔" : "λάθος"}
								</Badge>
							</div>

							{/* Σωστή απάντηση μόνο αν είναι λάθος */}
							{!a.correct && (
								<div className="text-xs text-muted-foreground">
									{renderCorrectAnswer(a)}
								</div>
							)}

							{/* ShortText ειδικό badge όπως πριν */}
							{a.type === "shortText" && a.correct && a.hasSpellingErrors && (
								<div className="text-xs text-muted-foreground">
									Σωστό με ορθογραφικές αποκλίσεις
								</div>
							)}
						</div>
					))}
				</div>
			</CardContent>
		</Card>
	)
}

export default LanguageGradingSummary
