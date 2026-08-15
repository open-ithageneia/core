import type { FeatureCollection, Geometry } from "geojson"
import { useCallback, useMemo, useRef, useState } from "react"
import type {
	RegionLabel,
	RegionValidation,
} from "@/components/quiz/shared/greece-map"
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

/**
 * Reveal, on every accepted region, the answer it belonged to.
 *
 * A region is skipped for a group that was already credited there — its own
 * chip is on the map already. Everywhere else the answer is spelled out: as an
 * ``alternative`` when the group was credited on one of its other regions (one
 * was all it needed), otherwise as the ``correct`` answer the user missed.
 */
function appendRevealedAnswers(
	labels: Map<string, RegionLabel[]>,
	texts: MapPointerTextGroup[],
	answerToRegions: Map<number, string[]>,
	creditedGroups: Set<number>,
	creditedByRegion: Map<string, Set<number>>,
) {
	for (const [idx, regionIds] of answerToRegions.entries()) {
		const credited = creditedGroups.has(idx)
		for (const regionId of regionIds) {
			if (creditedByRegion.get(regionId)?.has(idx)) {
				continue
			}
			const existing = labels.get(regionId) ?? []
			existing.push({
				text: texts[idx].alternatives[0],
				state: credited ? "alternative" : "correct",
			})
			labels.set(regionId, existing)
		}
	}
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

	/**
	 * Reverse map: region ID → every answer group that accepts it. Several
	 * answers may share a polygon, so a region can answer to more than one.
	 */
	const regionToAnswers = useMemo(() => {
		const map = new Map<string, number[]>()
		for (const [idx, regionIds] of answerToRegions.entries()) {
			for (const regionId of regionIds) {
				const accepting = map.get(regionId) ?? []
				accepting.push(idx)
				map.set(regionId, accepting)
			}
		}
		return map
	}, [answerToRegions])

	/** All region IDs that are valid targets in this quiz */
	const validRegionIds = useMemo(
		() => new Set(regionToAnswers.keys()),
		[regionToAnswers],
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
	/**
	 * Map: region_id → placed labels, in the order they were dropped. A region
	 * holds a stack rather than a single label because several answers may share
	 * a polygon and each has to be placeable on it.
	 */
	const [placements, setPlacements] = useState<Map<string, string[]>>(new Map())

	const placeLabel = useCallback(
		(regionId: string, label: string) => {
			if (showValidation) {
				return
			}
			setPlacements((prev) => {
				const next = new Map(prev)
				next.set(regionId, [...(prev.get(regionId) ?? []), label])
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
		[showValidation],
	)

	/** Take the last label off a region and return it to the bank. */
	const removeLabel = useCallback(
		(regionId: string) => {
			if (showValidation) {
				return
			}
			const stack = placements.get(regionId)
			if (!stack || stack.length === 0) {
				return
			}
			const label = stack[stack.length - 1]
			setPlacements((prev) => {
				const next = new Map(prev)
				const rest = (prev.get(regionId) ?? []).slice(0, -1)
				if (rest.length === 0) {
					next.delete(regionId)
				} else {
					next.set(regionId, rest)
				}
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
			// Read latest selectedLabel from ref (avoids stale closure)
			const label = selectedLabelRef.current
			// A selected label always stacks onto the region, even one that already
			// holds others — that is how two answers land on a shared polygon.
			if (label) {
				placeLabel(regionId, label)
				return
			}
			// Nothing selected: clicking a region takes its last label back off.
			removeLabel(regionId)
		},
		[showValidation, placeLabel, removeLabel],
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
	 * the regions its answer group accepts. Labels are judged one by one, so a
	 * shared polygon can hold a right and a wrong answer at the same time.
	 */
	const dropValidation = useMemo(() => {
		if (!showValidation) {
			return {
				regionStates: new Map<string, RegionValidation>(),
				correctGroupIndices: new Set<number>(),
				labels: new Map<string, RegionLabel[]>(),
			}
		}
		const regionStates = new Map<string, RegionValidation>()
		const correctGroupIndices = new Set<number>()
		/** region → the groups whose own label was correctly placed there */
		const correctByRegion = new Map<string, Set<number>>()
		const labels = new Map<string, RegionLabel[]>()

		for (const [regionId, stack] of placements.entries()) {
			const chips: RegionLabel[] = []
			let anyCorrect = false
			for (const label of stack) {
				// Find which answer group this label belongs to
				const groupIdx = texts.findIndex((g) => g.alternatives[0] === label)
				const isCorrect =
					groupIdx !== -1 &&
					(answerToRegions.get(groupIdx)?.includes(regionId) ?? false)
				chips.push({
					text: label,
					state: isCorrect ? "correct" : "incorrect",
					// A wrong label is struck through; the right answer for the region
					// is appended below it by appendRevealedAnswers.
					struck: !isCorrect,
				})
				if (isCorrect) {
					anyCorrect = true
					correctGroupIndices.add(groupIdx)
					const credited = correctByRegion.get(regionId) ?? new Set<number>()
					credited.add(groupIdx)
					correctByRegion.set(regionId, credited)
				}
			}
			if (chips.length === 0) {
				continue
			}
			labels.set(regionId, chips)
			// One right answer is enough to colour the region: any wrong label
			// stacked beside it still shows red on its own chip.
			regionStates.set(regionId, anyCorrect ? "correct" : "incorrect")
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
		appendRevealedAnswers(
			labels,
			texts,
			answerToRegions,
			correctGroupIndices,
			correctByRegion,
		)
		return { regionStates, correctGroupIndices, labels }
	}, [showValidation, placements, texts, answerToRegions])

	const dropValidationMap = dropValidation.regionStates

	/** Labels drawn on the map in drop mode, before and after validation. */
	const dropRegionLabels = useMemo(() => {
		if (showValidation) {
			return dropValidation.labels
		}
		const map = new Map<string, RegionLabel[]>()
		for (const [regionId, stack] of placements.entries()) {
			map.set(
				regionId,
				stack.map((text) => ({ text, state: "placed" as const })),
			)
		}
		return map
	}, [showValidation, dropValidation.labels, placements])

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

	/** Every label is down — regions may hold several, so count them, not regions. */
	const isDropComplete = useMemo(
		() =>
			[...placements.values()].reduce((n, stack) => n + stack.length, 0) ===
			texts.length,
		[placements, texts],
	)

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
				placedGroupIndices: new Set<number>(),
				alternativeRegionIds: new Set<string>(),
				matchedByRegion: new Map<string, Set<number>>(),
			}
		}
		/** Groups whose text was typed correctly, on any region right or wrong */
		const matchedGroupIndices = new Set<number>()
		/** Groups whose text was typed on one of the regions they accept */
		const placedGroupIndices = new Set<number>()
		const regionStates = new Map<string, ValidationState>()
		/** region → the groups credited by the answer typed there */
		const matchedByRegion = new Map<string, Set<number>>()
		const creditAt = (regionId: string, idx: number) => {
			matchedGroupIndices.add(idx)
			placedGroupIndices.add(idx)
			const credited = matchedByRegion.get(regionId) ?? new Set<number>()
			credited.add(idx)
			matchedByRegion.set(regionId, credited)
		}
		for (const [regionId, answer] of typeAnswers.entries()) {
			const norm = normalizeForTextComparison(answer)
			if (norm.length === 0) {
				regionStates.set(regionId, ValidationStatus.Incorrect)
				continue
			}
			// Any answer group that accepts this region will do — a shared polygon
			// answers to each of them, so the typed text is matched against them all.
			const accepting = regionToAnswers.get(regionId) ?? []
			const matching = accepting.filter((idx) =>
				texts[idx].alternatives.some(
					(alt) => normalizeForTextComparison(alt) === norm,
				),
			)
			if (matching.length > 0) {
				// Credit a group that has not scored yet where possible; when they all
				// have, the region is still correct — the score counts groups, not
				// regions, so an answer repeated on a second accepted region is free.
				creditAt(
					regionId,
					matching.find((idx) => !matchedGroupIndices.has(idx)) ?? matching[0],
				)
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
		// Placement is what counts here: an answer typed somewhere it is not
		// accepted has not landed anywhere, so its regions stay mistakes.
		const alternativeRegionIds = new Set<string>()
		for (const [idx, regionIds] of answerToRegions.entries()) {
			const answered = placedGroupIndices.has(idx)
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
		return {
			regionStates,
			matchedGroupIndices,
			placedGroupIndices,
			alternativeRegionIds,
			matchedByRegion,
		}
	}, [showValidation, typeAnswers, texts, regionToAnswers, answerToRegions])

	const typeTypedCount = typeValidation.matchedGroupIndices.size
	const typePlacedCount = typeValidation.placedGroupIndices.size

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

	/** Labels drawn on the map in type mode, before and after validation. */
	const typeRegionLabels = useMemo(() => {
		const map = new Map<string, RegionLabel[]>()
		if (!showValidation) {
			for (const [regionId, answer] of typeAnswers.entries()) {
				map.set(regionId, [{ text: answer, state: "placed" }])
			}
			return map
		}
		// The typed answer first, then the answer(s) the region really belonged to.
		for (const [regionId, answer] of typeAnswers.entries()) {
			const isCorrect =
				typeValidation.regionStates.get(regionId) === ValidationStatus.Correct
			map.set(regionId, [
				{
					text: answer,
					state: isCorrect ? "correct" : "incorrect",
					struck: !isCorrect,
				},
			])
		}
		// Credit here means placement: an answer typed on a region that does not
		// accept it is spelled out on the regions it did belong to.
		appendRevealedAnswers(
			map,
			texts,
			answerToRegions,
			typeValidation.placedGroupIndices,
			typeValidation.matchedByRegion,
		)
		return map
	}, [
		showValidation,
		typeAnswers,
		typeValidation.regionStates,
		typeValidation.placedGroupIndices,
		typeValidation.matchedByRegion,
		answerToRegions,
		texts,
	])

	// ─── Unified return ─────────────────────────────────────────────────

	const minCorrectAnswers = item.content.min_correct_answers

	/**
	 * Points available for the question.
	 *
	 * Drop mode asks one thing of each answer — put the chip on the right region
	 * — so it is worth one point per label. Type mode asks two: name the answer
	 * and put it on the region it belongs to. Each of those is scored on its own
	 * against ``min_correct_answers``, so the question is worth twice that:
	 *
	 *     (correct typed + correct placed) / (min_correct_answers * 2)
	 */
	const totalScore = isDropMode ? texts.length : minCorrectAnswers * 2

	/**
	 * Points earned. In type mode a right answer typed on the wrong region still
	 * earns its typing point — only the placement point is lost. Each half is
	 * capped at ``min_correct_answers`` so answering beyond the minimum asked
	 * cannot push the question over 100%.
	 */
	const correctAnswersCount = isDropMode
		? dropCorrectCount
		: Math.min(typeTypedCount, minCorrectAnswers) +
			Math.min(typePlacedCount, minCorrectAnswers)

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
		dropRegionLabels,
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
		typeRegionLabels,
		handleTypeRegionClick,
		updateTypeAnswer,
		clearTypeAnswer,
		minCorrectAnswers,
	}
}
