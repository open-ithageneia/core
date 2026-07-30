import type { FeatureCollection, Geometry } from "geojson"
import { useCallback, useMemo, useRef, useState } from "react"
import type { RegionValidation } from "@/components/quiz/shared/greece-map"
import { getGeoJson, type RegionProperties } from "@/geo/util"
import { useValidation } from "@/hooks/quiz/use-validation"
import { normalizeForTextComparison, shuffleArray } from "@/lib/utils"
import { ValidationStatus } from "@/types/enums"
import type { MapPointerModel, MapPointerTextGroup } from "@/types/models"
import type { ValidationState } from "@/types/quiz"

type UseMapPointerOptions = {
	forceValidation?: boolean
}

/**
 * Resolve which GeoJSON region IDs an answer group accepts.
 *
 * A group may list several areas — an answer that spans more than one area
 * (a river crossing several prefectures, say) is correct on any of them — so
 * each group maps to a list of accepted region IDs. Uses the explicit `areas`
 * names when available, falls back to matching alternatives against area names.
 */
function resolveRegionIds(
	texts: MapPointerTextGroup[],
	geojson: FeatureCollection<Geometry, RegionProperties>,
): Map<number, string[]> {
	const findRegionId = (name: string): string | undefined => {
		const norm = normalizeForTextComparison(name)
		return geojson.features.find(
			(f) => normalizeForTextComparison(f.properties.name) === norm,
		)?.properties.id
	}

	const map = new Map<number, string[]>()
	for (let i = 0; i < texts.length; i++) {
		const group = texts[i]
		// Prefer explicit area references
		const regionIds: string[] = []
		for (const area of group.areas ?? []) {
			const id = findRegionId(area)
			if (id && !regionIds.includes(id)) {
				regionIds.push(id)
			}
		}
		if (regionIds.length > 0) {
			map.set(i, regionIds)
			continue
		}
		// Fallback: match alternatives against GeoJSON names
		for (const alt of group.alternatives) {
			const id = findRegionId(alt)
			if (id) {
				map.set(i, [id])
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

	/** Map: answer group index → every GeoJSON region ID it accepts */
	const answerToRegions = useMemo(
		() => resolveRegionIds(texts, geojson),
		[texts, geojson],
	)

	/** Reverse map: region ID → answer group index */
	const regionToAnswer = useMemo(() => {
		const map = new Map<string, number>()
		for (const [idx, regionIds] of answerToRegions.entries()) {
			for (const regionId of regionIds) {
				map.set(regionId, idx)
			}
		}
		return map
	}, [answerToRegions])

	/** All region IDs that are valid targets in this quiz */
	const validRegionIds = useMemo(
		() => new Set(regionToAnswer.keys()),
		[regionToAnswer],
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
			if (showValidation) {
				return
			}
			if (placements.has(regionId)) {
				return
			}
			setPlacements((prev) => {
				const next = new Map(prev)
				next.set(regionId, label)
				return next
			})
			setAvailableLabels((prev) => {
				const idx = prev.indexOf(label)
				if (idx === -1) {
					return prev
				}
				return [...prev.slice(0, idx), ...prev.slice(idx + 1)]
			})
			setSelectedLabel(null)
		},
		[showValidation, placements],
	)

	const removeLabel = useCallback(
		(regionId: string) => {
			if (showValidation) {
				return
			}
			const label = placements.get(regionId)
			if (!label) {
				return
			}
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
			if (showValidation) {
				return
			}
			// If region already has a placement, remove it (acts as X button)
			if (placements.has(regionId)) {
				removeLabel(regionId)
				return
			}
			// Read latest selectedLabel from ref (avoids stale closure)
			const label = selectedLabelRef.current
			if (!label) {
				return
			}
			placeLabel(regionId, label)
		},
		[showValidation, placements, placeLabel, removeLabel],
	)

	const toggleLabelSelection = useCallback(
		(label: string) => {
			if (showValidation) {
				return
			}
			setSelectedLabel((prev) => (prev === label ? null : label))
		},
		[showValidation],
	)

	/**
	 * Validate drop mode: a placed label is correct when its region is one of
	 * the regions its answer group accepts.
	 */
	const dropValidation = useMemo(() => {
		if (!showValidation) {
			return {
				regionStates: new Map<string, RegionValidation>(),
				correctGroupIndices: new Set<number>(),
			}
		}
		const regionStates = new Map<string, RegionValidation>()
		const correctGroupIndices = new Set<number>()
		for (const [regionId, label] of placements.entries()) {
			// Find which answer group this label belongs to
			const groupIdx = texts.findIndex((g) => g.alternatives[0] === label)
			const isCorrect =
				groupIdx !== -1 &&
				(answerToRegions.get(groupIdx)?.includes(regionId) ?? false)
			regionStates.set(regionId, isCorrect ? "correct" : "incorrect")
			if (isCorrect) {
				correctGroupIndices.add(groupIdx)
			}
		}
		// The accepted regions left over: mistakes if the answer never landed on
		// any of them, otherwise alternatives — one of them was all it needed.
		for (const [idx, regionIds] of answerToRegions.entries()) {
			const answered = correctGroupIndices.has(idx)
			for (const regionId of regionIds) {
				if (!regionStates.has(regionId)) {
					regionStates.set(regionId, answered ? "alternative" : "incorrect")
				}
			}
		}
		return { regionStates, correctGroupIndices }
	}, [showValidation, placements, texts, answerToRegions])

	const dropValidationMap = dropValidation.regionStates

	const dropCorrectAnswersMap = useMemo(() => {
		if (!showValidation) {
			return new Map<string, string>()
		}
		// Name the answer each unplaced region belonged to, whether it was missed
		// or merely an alternative.
		const map = new Map<string, string>()
		for (const [idx, regionIds] of answerToRegions.entries()) {
			for (const regionId of regionIds) {
				if (dropValidation.regionStates.get(regionId) === "correct") {
					continue
				}
				map.set(regionId, texts[idx].alternatives[0])
			}
		}
		return map
	}, [showValidation, dropValidation.regionStates, answerToRegions, texts])

	const dropCorrectCount = dropValidation.correctGroupIndices.size

	/** Labels that were not placed on any of their accepted regions */
	const dropMissedAnswers = useMemo(() => {
		if (!showValidation) {
			return []
		}
		return texts
			.filter((_, i) => !dropValidation.correctGroupIndices.has(i))
			.map((g) => g.alternatives[0])
	}, [showValidation, dropValidation.correctGroupIndices, texts])

	const isDropComplete = placements.size === texts.length

	// ─── Mode 2: Type mode (show_answers=false) ─────────────────────────

	/** The region the user clicked on to type an answer */
	const [selectedTypeRegion, setSelectedTypeRegion] = useState<string | null>(
		null,
	)
	/** Map: region_id → typed answer */
	const [typeAnswers, setTypeAnswers] = useState<Map<string, string>>(new Map())

	const hasAtLeastOneAnswer = useMemo(
		() => [...typeAnswers.values()].some((a) => a.trim().length > 0),
		[typeAnswers],
	)

	const handleTypeRegionClick = useCallback(
		(regionId: string) => {
			if (showValidation) {
				return
			}
			setSelectedTypeRegion((prev) => (prev === regionId ? null : regionId))
		},
		[showValidation],
	)

	const updateTypeAnswer = useCallback(
		(regionId: string, value: string) => {
			if (showValidation) {
				return
			}
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
			if (showValidation) {
				return
			}
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
			return {
				regionStates: new Map<string, ValidationState>(),
				matchedGroupIndices: new Set<number>(),
				alternativeRegionIds: new Set<string>(),
			}
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
			if (
				answerIdx !== undefined &&
				texts[answerIdx].alternatives.some(
					(alt) => normalizeForTextComparison(alt) === norm,
				)
			) {
				// Correct even if the group was already matched on one of its other
				// accepted regions — the score counts groups, not regions.
				matchedGroupIndices.add(answerIdx)
				regionStates.set(regionId, ValidationStatus.Correct)
				continue
			}
			// Also check all groups in case user typed a correct answer on the wrong region
			let found = false
			for (let i = 0; i < texts.length; i++) {
				if (matchedGroupIndices.has(i)) {
					continue
				}
				if (
					texts[i].alternatives.some(
						(alt) => normalizeForTextComparison(alt) === norm,
					)
				) {
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
		// The accepted regions left unanswered: mistakes if the answer never
		// landed on any of them, otherwise alternatives — one was all it needed.
		const alternativeRegionIds = new Set<string>()
		for (const [idx, regionIds] of answerToRegions.entries()) {
			const answered = matchedGroupIndices.has(idx)
			for (const regionId of regionIds) {
				if (regionStates.has(regionId)) {
					continue
				}
				if (answered) {
					alternativeRegionIds.add(regionId)
				} else {
					regionStates.set(regionId, ValidationStatus.Incorrect)
				}
			}
		}
		return { regionStates, matchedGroupIndices, alternativeRegionIds }
	}, [showValidation, typeAnswers, texts, regionToAnswer, answerToRegions])

	const typeCorrectCount = typeValidation.matchedGroupIndices.size

	const missedAnswers = useMemo(() => {
		if (!showValidation) {
			return []
		}
		return texts
			.filter((_, i) => !typeValidation.matchedGroupIndices.has(i))
			.map((g) => g.alternatives[0])
	}, [showValidation, texts, typeValidation.matchedGroupIndices])

	/** Validation map for the GreeceMap in type mode */
	const typeValidationMap = useMemo(() => {
		if (!showValidation) {
			return undefined
		}
		const map = new Map<string, RegionValidation>()
		for (const [regionId, state] of typeValidation.regionStates.entries()) {
			map.set(
				regionId,
				state === ValidationStatus.Correct ? "correct" : "incorrect",
			)
		}
		for (const regionId of typeValidation.alternativeRegionIds) {
			map.set(regionId, "alternative")
		}
		return map
	}, [
		showValidation,
		typeValidation.regionStates,
		typeValidation.alternativeRegionIds,
	])

	/** Correct answers to show on the map after validation in type mode */
	const typeCorrectAnswersMap = useMemo(() => {
		if (!showValidation) {
			return undefined
		}
		// Name the answer each unanswered region belonged to, whether it was
		// missed or merely an alternative.
		const map = new Map<string, string>()
		for (const [idx, regionIds] of answerToRegions.entries()) {
			for (const regionId of regionIds) {
				if (
					typeValidation.regionStates.get(regionId) === ValidationStatus.Correct
				) {
					continue
				}
				map.set(regionId, texts[idx].alternatives[0])
			}
		}
		return map
	}, [showValidation, typeValidation.regionStates, answerToRegions, texts])

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
