// frontend/src/test-full/pages/LanguagePagePicker.tsx

import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import rawTestData from "../data/draftLanguageTests.json"
import type { LanguageFullTestType } from "../types/language.types"
import LanguageQuestion from "./languageQuestion"

const testData = rawTestData as LanguageFullTestType[]

const LanguagePagePicker = () => {
	const [chosenTest, setChosenTest] = useState<LanguageFullTestType | null>(
		null,
	)

	const activeTests = useMemo(() => {
		return testData
			.filter((t) => t.active !== false)
			.sort((a, b) => {
				const getNum = (title: string) => {
					const match = title.match(/ΘΕΜΑ\s+(\d+)/)
					return match ? Number(match[1]) : 0
				}
				return getNum(a.title) - getNum(b.title)
			})
	}, [])

	const handleRandom = () => {
		if (activeTests.length === 0) return
		const randomIndex = Math.floor(Math.random() * activeTests.length)
		setChosenTest(activeTests[randomIndex])
	}

	const handleSelect = (index: number) => {
		setChosenTest(activeTests[index])
	}

	return (
		<div className="max-w-3xl mx-auto py-10 space-y-6">
			{!chosenTest && (
				<div className="space-y-4">
					<select
						className="border p-2 w-full"
						defaultValue=""
						onChange={(e) => handleSelect(Number(e.target.value))}
					>
						<option value="" disabled>
							Επιλέξτε θέμα
						</option>

						{activeTests.map((test, index) => (
							<option key={test.id} value={index}>
								{test.title}
							</option>
						))}
					</select>

					<Button onClick={handleRandom}>Τυχαίο Θέμα</Button>
				</div>
			)}

			{chosenTest && <LanguageQuestion test={chosenTest} />}
		</div>
	)
}

export default LanguagePagePicker
