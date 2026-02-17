// frontend/src/test-full/components/QuestionMediaBlock.tsx

import type { QuestionMediaItem } from "../types/Full.types"

type Props = {
	media: QuestionMediaItem[]
}

// εξαγωγή γράμματος από filename (πχ 32a.jpg → a)
const extractLetter = (src: string): string => {
	const filename = src.split("/").pop() || ""
	const nameWithoutExt = filename.split(".")[0]

	const match = nameWithoutExt.match(/[a-zA-Z]$/)

	return match ? match[0] : ""
}

const QuestionMediaBlock = ({ media }: Props) => {
	if (!media || media.length === 0) return null

	return (
		<div className="grid gap-4 md:grid-cols-2">
			{media.map((item) => {
				const letter = extractLetter(item.src)

				return (
					<div key={item.id} className="flex flex-col items-center">
						<div className="relative">
							<img
								src={`${import.meta.env.BASE_URL}${item.src}`}
								alt={item.alt || ""}
								className="rounded border max-w-md"
							/>

							{letter && (
								<div className="absolute top-2 left-2 bg-black text-white px-2 py-1 rounded text-sm font-bold">
									{letter}
								</div>
							)}
						</div>

						{item.caption && (
							<p className="text-sm mt-2 text-muted-foreground">
								{item.caption}
							</p>
						)}
					</div>
				)
			})}
		</div>
	)
}

export default QuestionMediaBlock
