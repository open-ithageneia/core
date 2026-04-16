import MultipleChoice from "@/components/quiz/MultipleChoice"
import type { StatementModel } from "@/types/models"

type MultipleChoicePlaygroundProps = {
	multiple_choice_list: StatementModel[]
}

export default function MultipleChoicePlayground({
	multiple_choice_list,
}: MultipleChoicePlaygroundProps) {
	return (
		<section>
			{multiple_choice_list.map((item, index) => (
				<div key={item.id} className="py-5">
					<MultipleChoice item={item} item_index={index + 1} />
				</div>
			))}
		</section>
	)
}
