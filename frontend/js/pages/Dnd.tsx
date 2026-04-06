import DragNDrop from "@/components/quiz/DragNDrop"

type DndListProps = {
	// biome-ignore lint/suspicious/noExplicitAny: temporary until proper type is defined
	dnd_list: any[]
}

export default function Dnd({ dnd_list }: DndListProps) {
	return (
		<section>
			{/* {JSON.stringify(dnd_list)} */}
			{dnd_list.map((item) => (
				<DragNDrop key={item.id} item={item} />
			))}
		</section>
	)
}
