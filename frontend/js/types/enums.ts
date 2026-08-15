export enum QuizCategory {
	GEOGRAPHY = "GEOGRAPHY",
	CIVICS = "CIVICS",
	HISTORY = "HISTORY",
	CULTURE = "CULTURE",
	LISTENING = "LISTENING",
}

export const QUIZ_CATEGORY_LABELS: Record<QuizCategory, string> = {
	[QuizCategory.GEOGRAPHY]: "Γεωγραφία",
	[QuizCategory.CIVICS]: "Θεσμοί του Πολιτεύματος",
	[QuizCategory.HISTORY]: "Ιστορία",
	[QuizCategory.CULTURE]: "Πολιτισμός",
	[QuizCategory.LISTENING]: "Ακουστικό",
} as const

export enum StatementType {
	TRUE_FALSE = "TRUE_FALSE",
	MULTIPLE_CHOICE = "MULTIPLE_CHOICE",
}

/**
 * Names for the sections a listening question is split into, by position: the
 * parts themselves are unnamed on the server, so the naming lives here. Indexed
 * by the part's position in `ListeningModel.parts`.
 */
export const LISTENING_PART_LABELS = ["Μέρος Α", "Μέρος Β"] as const

/** Single Greek letter shown in the part badge, by position. */
export const LISTENING_PART_LETTERS = ["Α", "Β"] as const

/** Name of the part at *index*, falling back to its number past the letters. */
export function listeningPartLabel(index: number): string {
	return LISTENING_PART_LABELS[index] ?? `Μέρος ${index + 1}`
}

/** Badge letter of the part at *index*, falling back to its number. */
export function listeningPartLetter(index: number): string {
	return LISTENING_PART_LETTERS[index] ?? String(index + 1)
}

/** Administrative division level used by MapPointer questions (coarsest → finest). */
export enum MapLevel {
	/** Decentralized administrations (αποκεντρωμένες διοικήσεις) — GADM level 1 */
	DecentralizedAdmin = 1,
	/** Regions (περιφέρειες) — GADM level 2 */
	Region = 2,
	/** Prefecture units (νομοί / νησιά) */
	PrefectureUnit = 3,
	/** Municipalities and islands (δήμοι και νησιά) — GADM level 3 */
	Municipality = 4,
	/** Geographic departments (γεωγραφικά διαμερίσματα) — derived from level 3 */
	GeographicDepartment = 5,
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
	MAP_POINTER: "Τοποθετήστε κάθε επιλογή στη σωστή περιοχή του χάρτη",
	LISTENING: "Ακούστε το ηχητικό και απαντήστε στις ερωτήσεις",
} as const

export type QuizType = keyof typeof QUIZ_INSTRUCTIONS
