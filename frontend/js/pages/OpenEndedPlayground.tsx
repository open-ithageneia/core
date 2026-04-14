import OpenEnded from "@/components/quiz/OpenEnded"
import type { OpenEndedModel } from "@/types/models"

type OpenEndedListProps = {
	open_ended_list: OpenEndedModel[]
}

export default function OpenEndedPlayground({
	open_ended_list,
}: OpenEndedListProps) {
	return (
		<section>
			{open_ended_list.map((item, index) => (
				<div key={item.id} className="py-5">
					<OpenEnded
						key={item.id}
						item={item}
						item_index={index + 1}
					/>
				</div>
			))}
		</section>
	)
}
