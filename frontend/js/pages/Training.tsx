import { usePage } from "@inertiajs/react"
import { logger } from "@/lib/logger"
import type { TrainingData } from "@/types/models"

type TrainingProps = {
	data: TrainingData
}

export default function Training() {
	const { data } = usePage<{ data: TrainingProps }>().props

	logger.debug("Training data", data)

	return <h1>Training page</h1>
}
