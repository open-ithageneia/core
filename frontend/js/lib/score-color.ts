/**
 * Returns a CSS color string that interpolates from red (0) → orange (0.5) → green (1)
 * based on the ratio (0 to 1).
 */
export function getScoreColor(ratio: number): string {
	const clamped = Math.max(0, Math.min(1, ratio))
	// Hue: 0 (red) → 30 (orange) → 120 (green)
	const hue = clamped * 120
	return `hsl(${hue}, 80%, 40%)`
}
