// frontend\src\core-transfer\utils\formatGradedAnswer.tsx

// έχουμε πολλών διαφορετικών τύπων ερωτήσεις που επιστρέφουν answer με διαφορετικές μορφές και schema. Αυτή η helper func μου τα κάνει σε string
// πχ ["A", "B"] → "A, B", { A: "1", B: "2" } → "A: 1 | B: 2", { group1: ["A","B"] } → "group1: A, B"
// χρησιμοποιείται μόνο για feedback UI
export const formatCorrectAnswer = (answer: unknown): string => {
	if (!answer) return ""

	if (Array.isArray(answer)) {
		return answer.join(", ")
	}

	if (typeof answer === "object") {
		return Object.entries(answer)
			.map(([key, value]) =>
				Array.isArray(value)
					? `${key}: ${value.join(", ")}`
					: `${key}: ${String(value)}`,
			)
			.join(" | ")
	}

	return String(answer)
}
