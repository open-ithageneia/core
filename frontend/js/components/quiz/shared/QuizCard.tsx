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
		<Card className="flex h-full w-full flex-col rounded-2xl shadow-sm p-1">
			<CardHeader className="shrink-0 p-2">
				<CardTitle>{title}</CardTitle>
				{instruction && (
					<p className="text-sm text-muted-foreground">{instruction}</p>
				)}
				{promptText && <CardDescription>{promptText}</CardDescription>}
			</CardHeader>

			<CardContent className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2 pt-0">
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
