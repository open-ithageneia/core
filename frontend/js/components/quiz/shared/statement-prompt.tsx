import { CardDescription } from "@/components/ui/card"
import AudioPromptButton from "./audio-prompt-button"

type StatementPromptProps = {
	instruction?: string
	promptText?: string
	promptAssetUrl?: string
	promptAudioUrl?: string
}

/**
 * Renders the prompt block (instruction + audio/text prompt + image) for a
 * single statement. Used when a statement is embedded inside a combined card
 * (linked pair), where the shared {@link QuizCard} header can't host it.
 */
export default function StatementPrompt({
	instruction,
	promptText,
	promptAssetUrl,
	promptAudioUrl,
}: StatementPromptProps) {
	return (
		<div className="space-y-2">
			{instruction && (
				<p className="text-sm text-muted-foreground">{instruction}.</p>
			)}
			{promptAudioUrl ? (
				<AudioPromptButton url={promptAudioUrl} />
			) : (
				promptText && <CardDescription>{promptText}</CardDescription>
			)}
			{promptAssetUrl && (
				<img
					src={promptAssetUrl}
					alt={promptText ?? ""}
					className="max-h-40 rounded object-contain object-left sm:max-h-52 md:max-h-64 lg:max-h-80"
				/>
			)}
		</div>
	)
}
