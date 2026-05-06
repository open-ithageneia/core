import { createContext, type ReactNode, useContext } from "react"

type QuizResultsContextType = {
	badge?: ReactNode
}

const QuizResultsContext = createContext<QuizResultsContextType>({})

export function QuizResultsProvider({
	badge,
	children,
}: QuizResultsContextType & { children: ReactNode }) {
	return (
		<QuizResultsContext.Provider value={{ badge }}>
			{children}
		</QuizResultsContext.Provider>
	)
}

export function useQuizResults() {
	return useContext(QuizResultsContext)
}
