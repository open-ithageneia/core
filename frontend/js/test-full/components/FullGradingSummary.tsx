import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
// import MapClickQuiz from "../components/MapClickQuiz";
import type { FullAnswer, FullGradedAnswer } from "../types/Full.types"
import MapPointsGradingBlock from "./MapPointsGradingBlock"

type Props = {
	gradedAnswers: FullGradedAnswer[]
}

// βοηθητική μορφοποίηση για τα απλά question types
const formatAnswer = (answer: FullAnswer | undefined): string => {
	if (!answer) return "—"

	if (Array.isArray(answer)) {
		return answer.join(" / ")
	}

	if (typeof answer === "object") {
		return Object.entries(answer)
			.map(([key, value]) => `${key}-${value}`)
			.join(", ")
	}

	return answer
}

const GeographyFullGradingSummary = ({ gradedAnswers }: Props) => {
	const total = gradedAnswers.length
	const correctCount = gradedAnswers.filter((a) => a.correct).length

	return (
		<Card className="mt-4">
			<CardContent>
				<h3 className="mb-2 text-lg font-semibold">Αξιολόγηση</h3>

				{/* συνολικό σκορ */}
				<div className="mb-3">
					<Badge className="bg-primary text-primary-foreground">
						Σωστά: {correctCount} / {total}
					</Badge>
				</div>

				<ul className="space-y-4">
					{gradedAnswers.map((a, i) => (
						<li key={a.id} className="rounded-md border p-3 space-y-2">
							<p className="text-sm font-medium">{i + 1}.</p>

							{/* ΑΠΛΕΣ ΕΡΩΤΗΣΕΙΣ (όχι map) */}
							{a.type !== "mapPoints" && (
								<>
									<p className="text-sm">
										{formatAnswer(a.userAnswer)} →{" "}
										{formatAnswer(a.correctAnswer as FullAnswer)}
									</p>

									<Badge
										className={
											a.correct
												? "bg-primary text-primary-foreground"
												: "bg-destructive text-white"
										}
									>
										{a.correct
											? a.hasSpellingErrors
												? "σωστό (ορθογραφικό)"
												: "σωστό"
											: "λάθος"}
									</Badge>
								</>
							)}

							{/* MAP POINTS ΕΡΩΤΗΣΗ */}
							{a.type === "mapPoints" &&
								a.mapReviewPoints &&
								a.mapGradedPoints && (
									<>
										{/* Χάρτης με όλα τα σημεία (user + canonical) */}
										{/* <MapClickQuiz
                      points={a.mapReviewPoints}
                      setPoints={() => {}} // δεν επιτρέπουμε αλλαγές στο summary
                      maxPoints={a.mapReviewPoints.length}
                    /> */}

										{/* Αναλυτικό grading ανά σημείο */}
										<div className="space-y-1 text-sm">
											{a.type === "mapPoints" &&
												a.mapReviewPoints &&
												a.mapGradedPoints && (
													<MapPointsGradingBlock
														reviewPoints={a.mapReviewPoints}
														gradedPoints={a.mapGradedPoints}
													/>
												)}
										</div>
									</>
								)}
						</li>
					))}
				</ul>
			</CardContent>
		</Card>
	)
}

export default GeographyFullGradingSummary
