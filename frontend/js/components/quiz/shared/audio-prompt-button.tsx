import { Volume2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"
import { useQuizActive } from "./quiz-active-context"

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

function stopAudio(audio: HTMLAudioElement | null) {
	if (!audio) {
		return
	}
	audio.pause()
	audio.currentTime = 0
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
	const active = useQuizActive()

	const playsLeft = Math.max(maxPlays - playsUsed, 0)
	// Blocked while playing too, so a restart can't turn one attempt into a
	// partial replay of the clip.
	const disabled = playsLeft === 0 || isPlaying

	// A clip has to stop when its question is left, in both of the ways that can
	// happen: the card is hidden while staying mounted, which is how the quiz
	// pages move between questions, or the page goes away entirely. Neither stops
	// playback on its own — an audio element detached from the DOM keeps going.
	useEffect(() => {
		if (!active) {
			stopAudio(audioRef.current)
			return
		}
		// Read now rather than in the cleanup: React clears the ref before cleanups
		// run on unmount.
		const audio = audioRef.current
		return () => stopAudio(audio)
	}, [active])

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
				onPause={() => setIsPlaying(false)}
				onError={() => setIsPlaying(false)}
			/>
		</div>
	)
}
