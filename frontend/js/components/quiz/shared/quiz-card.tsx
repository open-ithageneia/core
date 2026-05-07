import type { ReactNode } from "react"

import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card"
import { QUIZ_CATEGORY_LABELS, type QuizCategory } from "@/types/enums"
import { useQuizResults } from "./quiz-results-context"

type QuizCardProps = {
	title: string
	category: QuizCategory
	badge?: ReactNode
	instruction?: string
	promptText?: string
	promptAssetUrl?: string
	headerExtra?: ReactNode
	children: ReactNode
}

export default function QuizCard({
	title,
	category,
	badge: badgeProp,
	instruction,
	promptText,
	promptAssetUrl,
	headerExtra,
	children,
}: QuizCardProps) {
	const { badge: contextBadge } = useQuizResults()
	const badge = badgeProp ?? contextBadge
	return (
		<Card className="flex h-full w-full flex-col rounded-2xl shadow-sm p-1">
			<CardHeader className="shrink-0 p-2">
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-2">
						<CardTitle>{title}</CardTitle>
						<CardDescription>{QUIZ_CATEGORY_LABELS[category]}</CardDescription>
					</div>
					{badge}
				</div>
				{instruction && (
					<p className="text-sm text-muted-foreground">{instruction}</p>
				)}
				{promptText && <CardDescription>{promptText}</CardDescription>}
			</CardHeader>

			{headerExtra && <div className="shrink-0 px-2">{headerExtra}</div>}

			<CardContent className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2 pt-1">
				{promptAssetUrl && (
					<img
						src={promptAssetUrl}
						alt={promptText ?? title}
						className="max-h-40 rounded object-contain object-left sm:max-h-52 md:max-h-64 lg:max-h-80"
					/>
				)}
				{children}
			</CardContent>
		</Card>
	)
}
