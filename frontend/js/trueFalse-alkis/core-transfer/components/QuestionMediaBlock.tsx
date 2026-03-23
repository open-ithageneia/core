// frontend/src/core-transfer/components/QuestionMediaBlock.tsx

type Props = {
	text?: string
	assetId?: number
}

const QuestionMediaBlock = ({ text, assetId }: Props) => {
	return (
		<div className="space-y-2">
			{text && <p>{text}</p>}

			{assetId && (
				<img
					// TODO CHECK!!!!
					src={`/assets/${assetId}.jpg`}
					alt="question"
					className="max-w-full rounded"
				/>
			)}
		</div>
	)
}

export default QuestionMediaBlock
