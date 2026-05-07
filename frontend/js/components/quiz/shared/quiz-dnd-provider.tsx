import { PointerActivationConstraints } from "@dnd-kit/dom"
import { DragDropProvider, PointerSensor } from "@dnd-kit/react"
import type { ReactNode } from "react"

type QuizDndProviderProps = {
	onDragEnd: (sourceValue: string, targetId: string) => void
	children: ReactNode
}

export default function QuizDndProvider({
	onDragEnd,
	children,
}: QuizDndProviderProps) {
	return (
		<DragDropProvider
			sensors={() => [
				PointerSensor.configure({
					activationConstraints: [
						new PointerActivationConstraints.Delay({
							value: 30,
							tolerance: 10,
						}),
					],
				}),
			]}
			onDragEnd={({ operation }) => {
				if (!operation.source || !operation.target) {
					return
				}
				onDragEnd(operation.source.data.value, String(operation.target.id))
			}}
		>
			{children}
		</DragDropProvider>
	)
}

