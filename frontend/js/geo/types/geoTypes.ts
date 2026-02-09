// ερώτησης γεωγραφίας
export type GeoQuestion = {
	id: string
	category: string
	ερώτηση: string
	rules?: {
		map?: boolean // αν είναι ερώτηση με χάρτη
		maxPoints?: number // πόσα σημεία επιτρέπονται
		tolerance?: boolean // αυτό είναι bool (δεν το έχω χρησιμοποιήσει γιατί βάζω απευθείας tolerancePct 3.5/8 )
		tolerancePct?: number // ανοχή σε %
		expectsSubset?: boolean // αυτό αφορά αλλλου τύπου έρωτήσεις (πχ 4 απο τους 12 θεους του ολύμπου. Αν και έχουμε και μία εδω)
		minItems?: number
		maxItems?: number
	}
	canonicalAnswer?: CanonicalPointsAnswer // σωστές απαντήσεις
}

// canonical απάντηση τύπου "points"
export type CanonicalPointsAnswer = {
	type: "points"
	points: {
		x: number
		y: number
		label: string
	}[]
}

// σημείο πάνω στον χάρτη (user ή απάντησης)
export type MapPoint = {
	x: number
	y: number
	label: string
}

// τύπος graded point
export type GradedPoint = MapPoint & {
	correct: boolean
	labelCorrect: boolean
	hasSpellingErrors: boolean
}

export type LabelCheckResult = {
	correct: boolean
	hasSpellingErrors: boolean
}
