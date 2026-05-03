import TrueFalse from "@/components/quiz/TrueFalse"
import type { StatementModel } from "@/types/models"

type TrueFalsePlaygroundProps = {
	true_false_list: StatementModel[]
}

export default function TrueFalsePlayground({
	true_false_list,
}: TrueFalsePlaygroundProps) {
	return (
		<section>
			{true_false_list.map((item, index) => (
				<div key={item.id} className="py-5">
					<TrueFalse item={item} item_index={index + 1} />
				</div>
			))}
		</section>
	)
}
