import type { ReactNode } from "react"

import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card"
import { useQuizCategoryLabel } from "@/hooks/use-quiz-category-label"
import { cn } from "@/lib/utils"
import type { QuizCategory } from "@/types/enums"
import AudioPromptButton from "./audio-prompt-button"
import { useQuizResults } from "./quiz-results-context"

type QuizCardProps = {
	title: string
	category: QuizCategory
	badge?: ReactNode
	instruction?: string
	promptText?: string
	promptAssetUrl?: string
	promptAudioUrl?: string
	/** Overrides the default play limit of the audio prompt. */
	promptAudioMaxPlays?: number
	headerExtra?: ReactNode
	/** Extra classes for the scrollable body, e.g. to lay children out as a column. */
	contentClassName?: string
	children: ReactNode
}

export default function QuizCard({
	title,
	category,
	badge: badgeProp,
	instruction,
	promptText,
	promptAssetUrl,
	promptAudioUrl,
	promptAudioMaxPlays,
	headerExtra,
	contentClassName,
	children,
}: QuizCardProps) {
	const { badge: contextBadge } = useQuizResults()
	const badge = badgeProp ?? contextBadge
	const categoryLabel = useQuizCategoryLabel()

	return (
		<Card className="flex h-full w-full flex-col rounded-2xl shadow-sm p-1">
			<CardHeader className="shrink-0 p-2">
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-1">
						<CardTitle>{title}</CardTitle>
						<CardDescription>{categoryLabel(category)}</CardDescription>
					</div>
					{badge}
				</div>

				<hr className="border-border" />
				{instruction && (
					<p className="text-sm text-muted-foreground">{instruction}.</p>
				)}
				{promptAudioUrl ? (
					<AudioPromptButton
						url={promptAudioUrl}
						maxPlays={promptAudioMaxPlays}
					/>
				) : (
					promptText && <CardDescription>{promptText}</CardDescription>
				)}
			</CardHeader>

			{headerExtra && <div className="shrink-0 px-2">{headerExtra}</div>}

			<CardContent
				className={cn(
					"min-h-0 flex-1 space-y-2 overflow-y-auto p-2 pt-0 mt-2",
					contentClassName,
				)}
			>
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
