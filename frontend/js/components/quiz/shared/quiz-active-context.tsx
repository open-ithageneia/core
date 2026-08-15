import { createContext, type ReactNode, useContext } from "react"

/**
 * Whether the question this subtree belongs to is the one currently on screen.
 *
 * The quiz pages keep every question mounted and only hide the ones that aren't
 * current, so moving to the next question destroys nothing — anything that
 * keeps running on its own, audio above all, has to be told its card was put
 * away. Defaults to true so a question rendered outside a provider behaves
 * normally.
 */
const QuizActiveContext = createContext(true)

export function QuizActiveProvider({
	active,
	children,
}: {
	active: boolean
	children: ReactNode
}) {
	return (
		<QuizActiveContext.Provider value={active}>
			{children}
		</QuizActiveContext.Provider>
	)
}

export function useQuizActive() {
	return useContext(QuizActiveContext)
}
