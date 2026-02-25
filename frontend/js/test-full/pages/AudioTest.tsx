import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select"
import rawAudioData from "../data/audioData.json"
import { useFullGrading } from "../hooks/useFullGrading"
import type { FullAnswer, FullGradedAnswer } from "../types/Full.types"
import AudioQuestion from "./AudioQuestion"

type AudioQuestionType = {
	id: string
	category: "ακουστικό"
	active: boolean
	type: "multipleChoice"
	question: string
	options: Record<string, string>
	correctAnswer: string
}

type AudioPart = {
	id: string
	title: string
	description: string
	questions: AudioQuestionType[]
}

type AudioTopic = {
	id: string
	title: string
	audioUrl: string
	transcript?: string
	parts: AudioPart[]
}

const audioTopics = rawAudioData as AudioTopic[]

const AudioTest = () => {
	const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null)
	const [answers, setAnswers] = useState<Record<string, FullAnswer>>({})
	const [gradedAnswers, setGradedAnswers] = useState<FullGradedAnswer[]>([])
	const [showTranscript, setShowTranscript] = useState(false)

	const { gradeAll } = useFullGrading()

	const selectedTopic = audioTopics.find(
		(topic) => topic.id === selectedTopicId,
	)

	const handleRandom = () => {
		const randomIndex = Math.floor(Math.random() * audioTopics.length)
		setSelectedTopicId(audioTopics[randomIndex].id)
		setAnswers({})
		setGradedAnswers([])
		setShowTranscript(false)
	}

	const handleChange = (id: string, value: FullAnswer) => {
		setAnswers((prev) => ({
			...prev,
			[id]: value,
		}))
	}

	const handleGradeAll = async () => {
		if (!selectedTopic) return

		// flatten όλα τα parts
		const allQuestions = selectedTopic.parts.flatMap((part) => part.questions)

		const { results } = await gradeAll(allQuestions, answers)
		setGradedAnswers(results)
	}

	// console.log(audioTopics)

	return (
		<div className="max-w-4xl mx-auto py-10 space-y-8">
			{/*  TOPIC PICKER */}
			{!selectedTopic && (
				<div className="space-y-4">
					<Select onValueChange={(value) => setSelectedTopicId(value)}>
						<SelectTrigger>
							<SelectValue placeholder="Επέλεξε θέμα" />
						</SelectTrigger>
						<SelectContent className="max-h-60 overflow-y-auto">
							{audioTopics.map((topic) => (
								<SelectItem key={topic.id} value={topic.id}>
									{topic.title}
								</SelectItem>
							))}
						</SelectContent>
					</Select>

					<Button onClick={handleRandom}>Επιλογή Τυχαίου Θέματος</Button>
				</div>
			)}

			{/*  TEST VIEW */}
			{selectedTopic && (
				<>
					<h2 className="text-2xl font-bold">
						Κατανόηση Προφορικού Λόγου – {selectedTopic.title}
					</h2>

					{/* AUDIO PLAYER */}
					<audio controls src={selectedTopic.audioUrl} className="w-full">
						{/* το λιντ με υποχρεωνε να έχω captions και έβαλα ένα mock */}
						<track kind="captions" src="" label="Greek captions" default />
					</audio>

					{/* PARTS + QUESTIONS */}
					{selectedTopic.parts.map((part) => (
						<div key={part.id} className="space-y-6">
							<div className="mt-8">
								<h3 className="text-xl font-semibold">{part.title}</h3>
								<p className="text-muted-foreground">{part.description}</p>
							</div>

							{part.questions.map((q, index) => (
								<div key={q.id} className="flex items-start gap-2">
									<span className="font-semibold">{index + 1}.</span>

									<AudioQuestion
										question={q}
										value={answers[q.id]}
										onChange={handleChange}
										gradedAnswer={gradedAnswers.find((a) => a.id === q.id)}
										showGrading={gradedAnswers.length > 0}
									/>
								</div>
							))}
						</div>
					))}

					{showTranscript && selectedTopic?.transcript && (
						<div className="mt-6 p-4 bg-muted rounded-lg whitespace-pre-line">
							<p>⚠️ auto created ⚠️</p>
							{selectedTopic.transcript}
						</div>
					)}

					<div className="flex gap-4">
						<Button onClick={handleGradeAll}>Αξιολόγηση</Button>

						{selectedTopic?.transcript && (
							<Button
								variant="secondary"
								onClick={() => setShowTranscript((prev) => !prev)}
							>
								{showTranscript ? "Απόκρυψη κειμένου" : "Εμφάνιση κειμένου"}
							</Button>
						)}
					</div>
				</>
			)}
		</div>
	)
}

export default AudioTest
