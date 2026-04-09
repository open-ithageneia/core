import DragAndDropQuiz from "@/components/quiz/DragAndDrop"
import type { DragAndDrop } from "@/types/models"

type DndListProps = {
	dnd_list: DragAndDrop[]
}

export default function Dnd({ dnd_list }: DndListProps) {
	return (
		<section>
			{dnd_list.map((item) => (
				<div key={item.id} className="py-5">
					<DragAndDropQuiz key={item.id} item={item} />
				</div>
			))}
		</section>
	)
}
