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
	promptText?: string
	children: ReactNode
}

export default function QuizCard({
	title,
	promptText,
	children,
}: QuizCardProps) {
	return (
		<Card className="w-full rounded-2xl shadow-sm">
			<CardHeader>
				<CardTitle>{title}</CardTitle>
				{promptText && <CardDescription>{promptText}</CardDescription>}
			</CardHeader>

			<CardContent className="space-y-6">{children}</CardContent>
		</Card>
	)
}
