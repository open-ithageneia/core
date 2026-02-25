// core\frontend\js\test-full\hooks\useEssayGrading.ts
import axios from "axios"
import { useState } from "react"
import { url } from "../constants/constants"
import type { EssayResult } from "../types/language.types"

type GradeEssayParams = {
	prompt: string
	studentText: string
}

export const useEssayGrading = () => {
	const [essayResult, setEssayResult] = useState<EssayResult | null>(null)
	const [essayLoading, setEssayLoading] = useState(false)

	const gradeEssay = async ({ prompt, studentText }: GradeEssayParams) => {
		if (!studentText) return

		try {
			setEssayLoading(true)

			const response = await axios.post(`${url}/api/grade/language/essay`, {
				prompt,
				studentText,
			})

			setEssayResult(response.data)
		} catch (err) {
			console.error(err)
		} finally {
			setEssayLoading(false)
		}
	}

	return {
		gradeEssay,
		essayResult,
		essayLoading,
	}
}
