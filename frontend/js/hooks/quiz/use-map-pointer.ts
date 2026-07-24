import { useCallback, useMemo, useRef, useState } from "react"
import { useValidation } from "@/hooks/quiz/use-validation"
import { normalizeForTextComparison, shuffleArray } from "@/lib/utils"
import { ValidationStatus } from "@/types/enums"
import type { MapPointerModel, MapPointerTextGroup } from "@/types/models"
import type { ValidationState } from "@/types/quiz"
import { getGeoJson, type RegionProperties } from "@/geo/util"
import type { FeatureCollection, Geometry } from "geojson"

type UseMapPointerOptions = {
	forceValidation?: boolean
}

/**
 * Resolve which GeoJSON region ID corresponds to each answer group.
 * Uses the explicit `area` name when available, falls back to matching
 * alternatives against prefecture names.
 */
function resolveRegionIds(
	texts: MapPointerTextGroup[],
	geojson: FeatureCollection<Geometry, RegionProperties>,
): Map<number, string> {
	const map = new Map<number, string>()
	for (let i = 0; i < texts.length; i++) {
		const group = texts[i]
		// Prefer explicit area reference
		if (group.area) {
			const match = geojson.features.find(
				(f) =>
					normalizeForTextComparison(f.properties.name) ===
					normalizeForTextComparison(group.area!),
			)
			if (match) {
				map.set(i, match.properties.id)
				continue
			}
		}
		// Fallback: match alternatives against GeoJSON names
		for (const alt of group.alternatives) {
			const normAlt = normalizeForTextComparison(alt)
			const match = geojson.features.find(
				(f) => normalizeForTextComparison(f.properties.name) === normAlt,
			)
			if (match) {
				map.set(i, match.properties.id)
				break
			}
		}
	}
	return map
}

export function useMapPointer(
	item: MapPointerModel,
	options?: UseMapPointerOptions,
) {
	const isDropMode = item.content.show_answers
	const texts = item.content.texts

	const { showValidation, setShowValidation, showValidationButton } =
		useValidation(options)

	/** GeoJSON for the question's administrative level */
	const geojson = useMemo(() => getGeoJson(item.level), [item.level])

	/** Map: answer group index → GeoJSON region ID */
	const answerToRegion = useMemo(
		() => resolveRegionIds(texts, geojson),
		[texts, geojson],
	)

	/** Reverse map: region ID → answer group index */
	const regionToAnswer = useMemo(() => {
		const map = new Map<string, number>()
		for (const [idx, regionId] of answerToRegion.entries()) {
			map.set(regionId, idx)
		}
		return map
	}, [answerToRegion])

	/** All region IDs that are valid targets in this quiz */
	const validRegionIds = useMemo(
		() => new Set(answerToRegion.values()),
		[answerToRegion],
	)

	/** Every region ID on the map — any region is a droppable target */
	const allRegionIds = useMemo(
		() => new Set(geojson.features.map((f) => f.properties.id)),
		[geojson],
	)

	// ─── Mode 1: Drop mode (show_answers=true) ──────────────────────────

	/** Shuffled labels (texts[i].alternatives[0]) for the chip bank */
	const allLabels = useMemo(
		() => shuffleArray(texts.map((g) => g.alternatives[0])),
		[texts],
	)

	const [availableLabels, setAvailableLabels] = useState<string[]>(allLabels)
	const [selectedLabel, setSelectedLabel] = useState<string | null>(null)
	const selectedLabelRef = useRef<string | null>(null)
	selectedLabelRef.current = selectedLabel
	/** Map: region_id → placed label text */
	const [placements, setPlacements] = useState<Map<string, string>>(new Map())

	const placeLabel = useCallback(
		(regionId: string, label: string) => {
			if (showValidation) return
			if (placements.has(regionId)) return
			setPlacements((prev) => {
				const next = new Map(prev)
				next.set(regionId, label)
				return next
			})
			setAvailableLabels((prev) => {
				const idx = prev.indexOf(label)
				if (idx === -1) return prev
				return [...prev.slice(0, idx), ...prev.slice(idx + 1)]
			})
			setSelectedLabel(null)
		},
		[showValidation, placements],
	)

	const removeLabel = useCallback(
		(regionId: string) => {
			if (showValidation) return
			const label = placements.get(regionId)
			if (!label) return
			setPlacements((prev) => {
				const next = new Map(prev)
				next.delete(regionId)
				return next
			})
			setAvailableLabels((prev) => [...prev, label])
		},
		[showValidation, placements],
	)

	const handleRegionClick = useCallback(
		(regionId: string) => {
			if (showValidation) return
			// If region already has a placement, remove it (acts as X button)
			if (placements.has(regionId)) {
				removeLabel(regionId)
				return
			}
			// Read latest selectedLabel from ref (avoids stale closure)
			const label = selectedLabelRef.current
			if (!label) return
			placeLabel(regionId, label)
		},
		[showValidation, placements, placeLabel, removeLabel],
	)

	const toggleLabelSelection = useCallback(
		(label: string) => {
			if (showValidation) return
			setSelectedLabel((prev) => (prev === label ? null : label))
		},
		[showValidation],
	)

	/** Validate drop mode: check if each placed label's answer group matches the region */
	const dropValidationMap = useMemo(() => {
		if (!showValidation) return new Map<string, "correct" | "incorrect">()
		const map = new Map<string, "correct" | "incorrect">()
		for (const [regionId, label] of placements.entries()) {
			// Find which answer group this label belongs to
			const groupIdx = texts.findIndex((g) => g.alternatives[0] === label)
			if (groupIdx === -1) {
				map.set(regionId, "incorrect")
				continue
			}
			// Check if this region is the correct region for this answer group
			const correctRegionId = answerToRegion.get(groupIdx)
			map.set(regionId, regionId === correctRegionId ? "correct" : "incorrect")
		}
		// Mark valid regions that were left unplaced as incorrect
		for (const regionId of validRegionIds) {
			if (!map.has(regionId)) {
				map.set(regionId, "incorrect")
			}
		}
		return map
	}, [showValidation, placements, texts, answerToRegion, validRegionIds])

	const dropCorrectAnswersMap = useMemo(() => {
		if (!showValidation) return new Map<string, string>()
		const map = new Map<string, string>()
		// Show correct label for wrongly-assigned regions
		for (const [regionId, result] of dropValidationMap.entries()) {
			if (result === "incorrect") {
				const answerIdx = regionToAnswer.get(regionId)
				if (answerIdx !== undefined) {
					map.set(regionId, texts[answerIdx].alternatives[0])
				}
			}
		}
		// Also show correct answer for unplaced regions
		for (const [idx, regionId] of answerToRegion.entries()) {
			if (!placements.has(regionId)) {
				map.set(regionId, texts[idx].alternatives[0])
			}
		}
		return map
	}, [showValidation, dropValidationMap, placements, regionToAnswer, answerToRegion, texts])

	const dropCorrectCount = useMemo(() => {
		let count = 0
		for (const v of dropValidationMap.values()) {
			if (v === "correct") count++
		}
		return count
	}, [dropValidationMap])

	/** Labels that were not placed on their correct region */
	const dropMissedAnswers = useMemo(() => {
		if (!showValidation) return []
		const missed: string[] = []
		for (const [idx, regionId] of answerToRegion.entries()) {
			const placement = placements.get(regionId)
			if (placement !== texts[idx].alternatives[0]) {
				missed.push(texts[idx].alternatives[0])
			}
		}
		return missed
	}, [showValidation, answerToRegion, placements, texts])

	const isDropComplete = placements.size === texts.length

	// ─── Mode 2: Type mode (show_answers=false) ─────────────────────────

	/** The region the user clicked on to type an answer */
	const [selectedTypeRegion, setSelectedTypeRegion] = useState<string | null>(null)
	/** Map: region_id → typed answer */
	const [typeAnswers, setTypeAnswers] = useState<Map<string, string>>(new Map())

	const hasAtLeastOneAnswer = useMemo(
		() => [...typeAnswers.values()].some((a) => a.trim().length > 0),
		[typeAnswers],
	)

	const handleTypeRegionClick = useCallback(
		(regionId: string) => {
			if (showValidation) return
			setSelectedTypeRegion((prev) => (prev === regionId ? null : regionId))
		},
		[showValidation],
	)

	const updateTypeAnswer = useCallback(
		(regionId: string, value: string) => {
			if (showValidation) return
			setTypeAnswers((prev) => {
				const next = new Map(prev)
				if (value === "") {
					next.delete(regionId)
				} else {
					next.set(regionId, value)
				}
				return next
			})
		},
		[showValidation],
	)

	const clearTypeAnswer = useCallback(
		(regionId: string) => {
			if (showValidation) return
			setTypeAnswers((prev) => {
				const next = new Map(prev)
				next.delete(regionId)
				return next
			})
			setSelectedTypeRegion(null)
		},
		[showValidation],
	)

	const typeValidation = useMemo(() => {
		if (!showValidation) {
			return { regionStates: new Map<string, ValidationState>(), matchedGroupIndices: new Set<number>() }
		}
		const matchedGroupIndices = new Set<number>()
		const regionStates = new Map<string, ValidationState>()
		for (const [regionId, answer] of typeAnswers.entries()) {
			const norm = normalizeForTextComparison(answer)
			if (norm.length === 0) {
				regionStates.set(regionId, ValidationStatus.Incorrect)
				continue
			}
			// Find which answer group corresponds to this region
			const answerIdx = regionToAnswer.get(regionId)
			if (answerIdx !== undefined && !matchedGroupIndices.has(answerIdx)) {
				if (texts[answerIdx].alternatives.some((alt) => normalizeForTextComparison(alt) === norm)) {
					matchedGroupIndices.add(answerIdx)
					regionStates.set(regionId, ValidationStatus.Correct)
					continue
				}
			}
			// Also check all groups in case user typed a correct answer on the wrong region
			let found = false
			for (let i = 0; i < texts.length; i++) {
				if (matchedGroupIndices.has(i)) continue
				if (texts[i].alternatives.some((alt) => normalizeForTextComparison(alt) === norm)) {
					matchedGroupIndices.add(i)
					regionStates.set(regionId, ValidationStatus.Incorrect)
					found = true
					break
				}
			}
			if (!found) {
				regionStates.set(regionId, ValidationStatus.Incorrect)
			}
		}
		// Regions with no answer are incorrect
		for (const regionId of validRegionIds) {
			if (!regionStates.has(regionId)) {
				regionStates.set(regionId, ValidationStatus.Incorrect)
			}
		}
		return { regionStates, matchedGroupIndices }
	}, [showValidation, typeAnswers, texts, regionToAnswer, validRegionIds])

	const typeCorrectCount = useMemo(() => {
		let count = 0
		for (const v of typeValidation.regionStates.values()) {
			if (v === ValidationStatus.Correct) count++
		}
		return count
	}, [typeValidation.regionStates])

	const missedAnswers = useMemo(() => {
		if (!showValidation) return []
		return texts
			.filter((_, i) => !typeValidation.matchedGroupIndices.has(i))
			.map((g) => g.alternatives[0])
	}, [showValidation, texts, typeValidation.matchedGroupIndices])

	/** Validation map for the GreeceMap in type mode */
	const typeValidationMap = useMemo(() => {
		if (!showValidation) return undefined
		const map = new Map<string, "correct" | "incorrect">()
		for (const [regionId, state] of typeValidation.regionStates.entries()) {
			map.set(regionId, state === ValidationStatus.Correct ? "correct" : "incorrect")
		}
		return map
	}, [showValidation, typeValidation.regionStates])

	/** Correct answers to show on the map after validation in type mode */
	const typeCorrectAnswersMap = useMemo(() => {
		if (!showValidation) return undefined
		const map = new Map<string, string>()
		for (const [regionId, state] of typeValidation.regionStates.entries()) {
			if (state === ValidationStatus.Incorrect) {
				const answerIdx = regionToAnswer.get(regionId)
				if (answerIdx !== undefined) {
					map.set(regionId, texts[answerIdx].alternatives[0])
				}
			}
		}
		return map
	}, [showValidation, typeValidation.regionStates, regionToAnswer, texts])

	// ─── Unified return ─────────────────────────────────────────────────

	const totalScore = texts.length
	const correctAnswersCount = isDropMode ? dropCorrectCount : typeCorrectCount

	return {
		isDropMode,
		// Shared
		showValidation,
		setShowValidation,
		showValidationButton,
		totalScore,
		correctAnswersCount,
		validRegionIds,
		allRegionIds,
		// Drop mode
		availableLabels,
		selectedLabel,
		placements,
		isDropComplete,
		dropValidationMap,
		dropCorrectAnswersMap,
		dropMissedAnswers,
		handleRegionClick,
		toggleLabelSelection,
		removeLabel,
		// Type mode
		selectedTypeRegion,
		typeAnswers,
		hasAtLeastOneAnswer,
		missedAnswers,
		typeValidationMap,
		typeCorrectAnswersMap,
		handleTypeRegionClick,
		updateTypeAnswer,
		clearTypeAnswer,
		minCorrectAnswers: item.content.min_correct_answers,
	}
}
