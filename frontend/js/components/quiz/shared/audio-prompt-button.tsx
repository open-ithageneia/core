import { Volume2 } from "lucide-react"
import { useRef } from "react"

export const AUDIO_PROMPT_TEXT =
	"Πατήστε το εικονίδιο για να ακούσετε την ερώτηση"

export default function AudioPromptButton({ url }: { url: string }) {
	const audioRef = useRef<HTMLAudioElement>(null)

	const playAudio = () => {
		const audio = audioRef.current
		if (!audio) {
			return
		}
		audio.currentTime = 0
		void audio.play()
	}

	return (
		<button
			type="button"
			onClick={playAudio}
			aria-label={AUDIO_PROMPT_TEXT}
			className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
		>
			<Volume2 className="h-6 w-6 shrink-0" aria-hidden="true" />
			<span>{AUDIO_PROMPT_TEXT}</span>
			{/* biome-ignore lint/a11y/useMediaCaption: audio prompt has no captions */}
			<audio ref={audioRef} src={url} preload="auto" />
		</button>
	)
}
