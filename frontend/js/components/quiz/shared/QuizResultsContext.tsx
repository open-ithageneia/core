import { createContext, type ReactNode, useContext } from "react"

type QuizResultsContextType = {
	badge?: ReactNode
	hideScore?: boolean
}

const QuizResultsContext = createContext<QuizResultsContextType>({})

export function QuizResultsProvider({
	badge,
	hideScore,
	children,
}: QuizResultsContextType & { children: ReactNode }) {
	return (
		<QuizResultsContext.Provider value={{ badge, hideScore }}>
			{children}
		</QuizResultsContext.Provider>
	)
}

export function useQuizResults() {
	return useContext(QuizResultsContext)
}
