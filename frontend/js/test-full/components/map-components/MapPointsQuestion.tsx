import { useState } from "react"
import type { GeoMapPointsQuestion, MapPoint } from "../../types/Full.types"

type MapPointsQuestionProps = {
	question: GeoMapPointsQuestion
	value?: MapPoint[] // controlled value από parent
	onChange: (value: MapPoint[]) => void
	readOnly?: boolean // μετά το submit
}

// component: δείχνει χάρτη + overlay για click
const MapPointsQuestion = ({
	question,
	value = [],
	onChange,
	readOnly = false,
}: MapPointsQuestionProps) => {
	const maxPoints = question.rules?.maxPoints ?? 4

	// προσωρινό σημείο (όσο γράφουμε πριν το submit)
	const [draftPoint, setDraftPoint] = useState<{ x: number; y: number } | null>(
		null,
	)

	// προσωρινό label για το draft σημείο
	const [label, setLabel] = useState("")

	// click πάνω στο overlay
	const handleClick = (e: React.MouseEvent<HTMLElement>) => {
		// αν υπάρχει ήδη draft ή έχουμε φτάσει το max ή είμαστε readOnly, μπλοκάρουμε
		if (draftPoint || value.length >= maxPoints || readOnly) return

		const rect = e.currentTarget.getBoundingClientRect()

		// ΧΡΗΣΙΜΟ: clientX/Y – rect.left/top
		const xPercentage = ((e.clientX - rect.left) / rect.width) * 100
		const yPercentage = ((e.clientY - rect.top) / rect.height) * 100

		setDraftPoint({ x: xPercentage, y: yPercentage })
		setLabel("")
	}

	const handleSubmit = () => {
		if (!draftPoint || !label.trim()) return

		// προσθέτουμε το σημείο στο controlled state του parent
		onChange([...value, { x: draftPoint.x, y: draftPoint.y, label }])

		// καθαρίζουμε μόνο το draft
		setDraftPoint(null)
		setLabel("")
	}

	const handleCancelDraft = () => {
		setDraftPoint(null)
		setLabel("")
	}

	const updatePointLabel = (index: number, newLabel: string) => {
		if (readOnly) return

		onChange(value.map((p, i) => (i === index ? { ...p, label: newLabel } : p)))
	}

	const removePoint = (index: number) => {
		if (readOnly) return

		// αν ακυρώσουμε ένα σημείο, ελευθερώνεται slot
		onChange(value.filter((_, i) => i !== index))
	}

	// styles για input + label (ίδια πριν & μετά submit)
	const compactInputStyle = {
		width: 70,
		height: 18,
		fontSize: 11,
		padding: "1px 3px",
		border: "1px solid #aaa",
		borderRadius: 3,
		outline: "none",
	}

	const compactBoxStyle = {
		display: "flex",
		gap: 3,
		background: "white",
		padding: "2px 3px",
		border: "1px solid #ccc",
		borderRadius: 4,
		zIndex: 10,
	}

	return (
		<div className="space-y-3">
			{/* Κείμενο ερώτησης */}
			<p className="font-medium">{question.question}</p>

			<div
				style={{
					position: "relative",
					width: "100%",
					maxWidth: 900,
				}}
			>
				{/* χάρτης */}
				<img
					src={`${import.meta.env.BASE_URL}mapOfGreecce.png`}
					alt="Χάρτης Ελλάδας"
					style={{
						width: "100%",
						height: "auto",
						display: "block",
					}}
				/>

				{/* overlay για click – ΙΔΙΟ container με τα points */}
				<button
					type="button"
					onClick={handleClick}
					style={{
						position: "absolute",
						inset: 0,
						cursor:
							draftPoint || value.length >= maxPoints || readOnly
								? "not-allowed"
								: "crosshair",
					}}
				/>

				{/* ήδη υποβληθέντα σημεία */}
				{value.map((p, index) => (
					<div key={`${p.x}-${p.y}-${p.label}`}>
						{/* κουκίδα */}
						<div
							style={{
								position: "absolute",
								left: `${p.x}%`,
								top: `${p.y}%`,
								transform: "translate(-50%, -50%)",
								width: 10,
								height: 10,
								borderRadius: "50%",
								backgroundColor: "red",
								pointerEvents: "none",
							}}
						/>

						{/* label δίπλα στην κουκίδα */}
						<div
							style={{
								position: "absolute",
								left: `${p.x}%`,
								top: `${p.y}%`,
								transform: "translate(10px, -50%)",
								...compactBoxStyle,
							}}
						>
							<input
								type="text"
								value={p.label}
								onChange={(e) => updatePointLabel(index, e.target.value)}
								placeholder="γράψε"
								style={compactInputStyle}
								disabled={readOnly}
							/>

							{!readOnly && (
								<button
									type="button"
									style={{ fontSize: 11 }}
									onClick={() => removePoint(index)}
								>
									✖
								</button>
							)}
						</div>
					</div>
				))}

				{/* draft κουκίδα + input */}
				{draftPoint && !readOnly && (
					<>
						<div
							style={{
								position: "absolute",
								left: `${draftPoint.x}%`,
								top: `${draftPoint.y}%`,
								transform: "translate(-50%, -50%)",
								width: 10,
								height: 10,
								borderRadius: "50%",
								backgroundColor: "blue",
								pointerEvents: "none",
							}}
						/>

						<div
							style={{
								position: "absolute",
								left: `${draftPoint.x}%`,
								top: `${draftPoint.y}%`,
								transform: "translate(10px, -50%)",
								...compactBoxStyle,
							}}
						>
							<input
								type="text"
								value={label}
								onChange={(e) => setLabel(e.target.value)}
								placeholder="γράψε"
								style={compactInputStyle}
							/>

							<button
								type="button"
								style={{ fontSize: 11 }}
								onClick={handleSubmit}
							>
								✔
							</button>

							<button
								type="button"
								style={{ fontSize: 11 }}
								onClick={handleCancelDraft}
							>
								✖
							</button>
						</div>
					</>
				)}
			</div>
		</div>
	)
}

export default MapPointsQuestion
