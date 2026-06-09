import { PointerActivationConstraints } from "@dnd-kit/dom"
import { DragDropProvider, PointerSensor } from "@dnd-kit/react"
import type { ReactNode } from "react"

type QuizDndProviderProps<T> = {
	onDragEnd: (sourceValue: T, targetId: string) => void
	children: ReactNode
}

export default function QuizDndProvider<T = string>({
	onDragEnd,
	children,
}: QuizDndProviderProps<T>) {
	return (
		<DragDropProvider
			sensors={() => [
				PointerSensor.configure({
					activationConstraints: [
						new PointerActivationConstraints.Delay({
							value: 150,
							tolerance: 5,
						}),
						new PointerActivationConstraints.Distance({
							value: 5,
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
