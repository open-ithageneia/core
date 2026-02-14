import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import type { EssayResult } from "@/languageTest/types/language.types"

type Props = {
	result: EssayResult
}

const EssayGradingSummary = ({ result }: Props) => {
	const { scores, total, feedback, modelAnswer } = result

	return (
		<Card className="mt-6">
			<CardContent className="space-y-4">
				<h3 className="text-lg font-semibold">Αξιολόγηση Γ Θέματος</h3>

				<div className="flex flex-wrap gap-2">
					{Object.entries(scores).map(([key, value]) => (
						<Badge key={key} className="bg-secondary">
							{key}: {Number(value)}/100
						</Badge>
					))}

					<Badge className="bg-primary text-primary-foreground">
						Σύνολο: {total}
					</Badge>
				</div>

				<div>
					<h4 className="font-semibold">Σχόλιο:</h4>
					<p className="text-sm text-muted-foreground">{feedback}</p>
				</div>

				<div>
					<h4 className="font-semibold">Υπόδειγμα Απάντησης:</h4>
					<p className="text-sm whitespace-pre-line">{modelAnswer}</p>
				</div>
			</CardContent>
		</Card>
	)
}

export default EssayGradingSummary
