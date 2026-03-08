import { usePage } from "@inertiajs/react"
import type { TrainingData } from "@/types/models"

type TrainingProps = {
	data: TrainingData
}

export default function Training() {
	const { data } = usePage<{ data: TrainingProps }>().props

	console.log(data)

	return <h1>Training page</h1>
}
