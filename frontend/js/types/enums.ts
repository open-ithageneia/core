export enum QuizCategory {
	GEOGRAPHY = "GEOGRAPHY",
	CIVICS = "CIVICS",
	HISTORY = "HISTORY",
	CULTURE = "CULTURE",
}

export const QUIZ_CATEGORY_LABELS: Record<QuizCategory, string> = {
	[QuizCategory.GEOGRAPHY]: "Γεωγραφία",
	[QuizCategory.CIVICS]: "Θεσμοί του Πολιτεύματος",
	[QuizCategory.HISTORY]: "Ιστορία",
	[QuizCategory.CULTURE]: "Πολιτισμός",
} as const

export enum StatementType {
	TRUE_FALSE = "TRUE_FALSE",
	MULTIPLE_CHOICE = "MULTIPLE_CHOICE",
}

export enum ValidationStatus {
	Correct = "correct",
	Incorrect = "incorrect",
}

export const QUIZ_INSTRUCTIONS = {
	TRUE_FALSE: "Επιλέξτε τη σωστή απάντηση",
	MULTIPLE_CHOICE_SINGLE: "Επιλέξτε τη σωστή απάντηση",
	MULTIPLE_CHOICE_MULTI: "Επιλέξτε τις σωστές απαντήσεις",
	DRAG_AND_DROP: "Σύρετε και αποθέστε στη σωστή θέση",
	MATCHING: "Αντιστοιχίστε τα σωστά ζεύγη",
	FILL_IN_THE_BLANK: "Συμπληρώστε τα κενά",
} as const

export type QuizType = keyof typeof QUIZ_INSTRUCTIONS
