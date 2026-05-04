import type { ReactNode } from "react"

import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card"

type QuizCardProps = {
	title: string
	instruction?: string
	promptText?: string
	promptAssetUrl?: string
	children: ReactNode
}

export default function QuizCard({
	title,
	instruction,
	promptText,
	promptAssetUrl,
	children,
}: QuizCardProps) {
	return (
		<Card className="flex h-full w-full flex-col rounded-2xl shadow-sm">
			<CardHeader className="shrink-0">
				<CardTitle>{title}</CardTitle>
				{instruction && (
					<p className="text-sm text-muted-foreground">{instruction}</p>
				)}
				{promptText && <CardDescription>{promptText}</CardDescription>}
				{promptAssetUrl && (
					<img
						src={promptAssetUrl}
						alt={promptText ?? title}
						className="mt-2 max-h-60 rounded object-contain"
					/>
				)}
			</CardHeader>

			<CardContent className="min-h-0 flex-1 space-y-6 overflow-y-auto">
				{children}
			</CardContent>
		</Card>
	)
}
