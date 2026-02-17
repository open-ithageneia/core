// frontend/src/geography-full/components/MapPointsGradingBlock.tsx

import { Badge } from "@/components/ui/badge"
import type { GradedPoint, MapPoint } from "../types/Full.types"
import MapClickQuiz from "./MapClickQuiz"

type Props = {
	reviewPoints: MapPoint[]
	gradedPoints: GradedPoint[]
}

const MapPointsGradingBlock = ({ reviewPoints, gradedPoints }: Props) => {
	return (
		<div className="space-y-3">
			{/* Χάρτης μόνο για προβολή (read-only) */}
			<MapClickQuiz
				points={reviewPoints}
				setPoints={() => {}}
				maxPoints={reviewPoints.length}
			/>

			{/* Αναλυτικό grading */}
			<div className="space-y-1 text-sm">
				{gradedPoints.map((p) => (
					<div key={`${p.x}-${p.y}-${p.label}`} className="flex flex-col gap-1">
						<span>
							({p.x.toFixed(1)}, {p.y.toFixed(1)}) → "{p.label}"
						</span>

						<div className="flex gap-2">
							{/* χωρική ακρίβεια */}
							<Badge
								className={
									p.correct
										? "bg-primary text-primary-foreground"
										: "bg-destructive text-white"
								}
							>
								{p.correct ? "σωστό σημείο" : "λάθος σημείο"}
							</Badge>

							{/* λεκτική ακρίβεια */}
							<Badge
								className={
									p.labelCorrect
										? "bg-secondary text-secondary-foreground"
										: "bg-destructive text-white"
								}
							>
								{p.labelCorrect
									? p.hasSpellingErrors
										? "σωστό λεκτικό (ορθογραφικό)"
										: "σωστό λεκτικό"
									: "λάθος λεκτικό"}
							</Badge>
						</div>
					</div>
				))}
			</div>
		</div>
	)
}

export default MapPointsGradingBlock
