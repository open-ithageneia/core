import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select"
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table"
import type { FullMatchingQuestion } from "../types/Full.types"
import QuestionMediaBlock from "./QuestionMediaBlock"

type Props = {
	question: FullMatchingQuestion
	value?: Record<string, string>
	onChange: (value: Record<string, string>) => void
}

const MatchingQuestionComponent = ({
	question,
	value = {},
	onChange,
}: Props) => {
	const handleSelect = (rowKey: string, selected: string) => {
		onChange({
			...value,
			[rowKey]: selected,
		})
	}

	return (
		<div className="space-y-6">
			{/* Εκφώνηση */}
			<p className="font-medium">{question.question}</p>

			{question.media && question.media.length > 0 && (
				<QuestionMediaBlock media={question.media} />
			)}

			{/* ===== ΣΤΑΤΙΚΟΣ ΠΙΝΑΚΑΣ ΕΚΦΩΝΗΣΗΣ ===== */}
			<Table className="w-full border border-black text-center">
				<TableHeader>
					<TableRow className="border-b border-black">
						<TableHead className="w-1/2 font-bold border-r border-black">
							Στήλη Ι
							<div className="font-semibold">{question.columnAHeader}</div>
						</TableHead>

						<TableHead className="w-1/2 font-bold">
							Στήλη ΙΙ
							<div className="font-semibold">{question.columnBHeader}</div>
						</TableHead>
					</TableRow>
				</TableHeader>

				<TableBody>
					{question.columnA.map((item, index) => (
						<TableRow key={item.key} className="border-b border-black">
							<TableCell className="border-r border-black font-semibold">
								{item.key}. {item.label}
							</TableCell>

							<TableCell className="font-semibold">
								{question.columnB[index]
									? `${question.columnB[index].key}. ${question.columnB[index].label}`
									: ""}
							</TableCell>
						</TableRow>
					))}
				</TableBody>
			</Table>

			{/* ===== INTERACTIVE MATCHING ===== */}
			<div>
				<p className="mb-2 font-semibold">Επιλέξτε την σωστή αντιστοίχιση:</p>

				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>Στήλη Ι</TableHead>
							<TableHead>Αντιστοίχιση</TableHead>
						</TableRow>
					</TableHeader>

					<TableBody>
						{question.columnA.map((item) => (
							<TableRow key={item.key}>
								<TableCell>
									{item.key}. {item.label}
								</TableCell>

								<TableCell>
									<Select
										value={value[item.key] ?? ""}
										onValueChange={(val) => handleSelect(item.key, val)}
									>
										<SelectTrigger className="w-52">
											<SelectValue placeholder="Επιλογή" />
										</SelectTrigger>

										<SelectContent>
											{question.columnB.map((opt) => (
												<SelectItem key={opt.key} value={opt.key}>
													{opt.key}. {opt.label}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</TableCell>
							</TableRow>
						))}
					</TableBody>
				</Table>
			</div>
		</div>
	)
}

export default MatchingQuestionComponent
