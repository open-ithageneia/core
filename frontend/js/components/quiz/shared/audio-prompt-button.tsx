import { Volume2 } from "lucide-react"
import { useRef, useState } from "react"
import { cn } from "@/lib/utils"

export const AUDIO_PROMPT_TEXT =
	"Πατήστε το εικονίδιο για να ακούσετε την ερώτηση"

export const AUDIO_PLAYING_TEXT = "Αναπαραγωγή σε εξέλιξη..."

/** Listening prompts may be heard at most this many times, as in the real exam. */
export const MAX_AUDIO_PLAYS = 2

function playsLeftText(playsLeft: number): string {
	if (playsLeft === 0) {
		return "Δεν απομένουν άλλες αναπαραγωγές."
	}
	if (playsLeft === 1) {
		return "Απομένει 1 αναπαραγωγή."
	}
	return `Απομένουν ${playsLeft} αναπαραγωγές.`
}

export default function AudioPromptButton({
	url,
	maxPlays = MAX_AUDIO_PLAYS,
}: {
	url: string
	maxPlays?: number
}) {
	const audioRef = useRef<HTMLAudioElement>(null)
	const [playsUsed, setPlaysUsed] = useState(0)
	const [isPlaying, setIsPlaying] = useState(false)

	const playsLeft = Math.max(maxPlays - playsUsed, 0)
	// Blocked while playing too, so a restart can't turn one attempt into a
	// partial replay of the clip.
	const disabled = playsLeft === 0 || isPlaying

	const playAudio = () => {
		const audio = audioRef.current
		if (!audio || disabled) {
			return
		}
		audio.currentTime = 0
		void audio.play()
	}

	return (
		<div className="space-y-1">
			<button
				type="button"
				onClick={playAudio}
				disabled={disabled}
				aria-label={AUDIO_PROMPT_TEXT}
				className={cn(
					"flex items-center gap-2 text-sm text-muted-foreground transition-colors",
					disabled ? "cursor-not-allowed opacity-60" : "hover:text-foreground",
				)}
			>
				<Volume2 className="h-6 w-6 shrink-0" aria-hidden="true" />
				<span>{isPlaying ? AUDIO_PLAYING_TEXT : AUDIO_PROMPT_TEXT}</span>
			</button>

			<p className="text-xs text-muted-foreground">
				Μπορείτε να ακούσετε το ηχητικό έως {maxPlays} φορές.{" "}
				<span
					aria-live="polite"
					className={cn("font-medium", playsLeft === 0 && "text-destructive")}
				>
					{playsLeftText(playsLeft)}
				</span>
			</p>

			{/* The play is counted from the element's own event, so a load failure
			    doesn't silently spend an attempt. */}
			{/* biome-ignore lint/a11y/useMediaCaption: audio prompt has no captions */}
			<audio
				ref={audioRef}
				src={url}
				preload="auto"
				onPlay={() => {
					setPlaysUsed((used) => used + 1)
					setIsPlaying(true)
				}}
				onEnded={() => setIsPlaying(false)}
				onError={() => setIsPlaying(false)}
			/>
		</div>
	)
}
