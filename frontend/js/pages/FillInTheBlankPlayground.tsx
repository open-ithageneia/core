import FillInTheBlank from "@/components/quiz/FillInTheBlank"
import type { FillInTheBlankModel } from "@/types/models"

type FillInTheBlankPlaygroundProps = {
	fill_in_the_blank_list: FillInTheBlankModel[]
}

export default function FillInTheBlankPlayground({
	fill_in_the_blank_list,
}: FillInTheBlankPlaygroundProps) {
	return (
		<section>
			{fill_in_the_blank_list.map((item, index) => (
				<div key={item.id} className="py-5">
					<FillInTheBlank item={item} item_index={index + 1} />
				</div>
			))}
		</section>
	)
}
