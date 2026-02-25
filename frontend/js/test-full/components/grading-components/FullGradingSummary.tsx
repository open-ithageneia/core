import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import type { FullAnswer, FullGradedAnswer } from "../../types/Full.types"
import MapPointsGradingBlock from "../map-components/MapPointsGradingBlock"

type Props = {
	gradedAnswers: FullGradedAnswer[]
}

const formatAnswer = (answer: FullAnswer | undefined): string => {
	if (!answer) return "—"

	if (Array.isArray(answer)) return answer.join(", ")

	if (typeof answer === "object")
		return Object.entries(answer)
			.map(([k, v]) => `${k}: ${v}`)
			.join(" | ")

	return String(answer)
}

const GeographyFullGradingSummary = ({ gradedAnswers }: Props) => {
	const total = gradedAnswers.length
	const correctCount = gradedAnswers.filter((a) => a.correct).length

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
							className="rounded-md border p-3 space-y-1 bg-muted/20"
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

							{a.type !== "mapPoints" && !a.correct && (
								<div className="text-xs text-muted-foreground">
									{formatAnswer(a.correctAnswer as FullAnswer)}
								</div>
							)}

							{a.type === "mapPoints" &&
								a.mapReviewPoints &&
								a.mapGradedPoints && (
									<div className="pt-1">
										<MapPointsGradingBlock
											reviewPoints={a.mapReviewPoints}
											gradedPoints={a.mapGradedPoints}
										/>
									</div>
								)}
						</div>
					))}
				</div>
			</CardContent>
		</Card>
	)
}

export default GeographyFullGradingSummary
