import L from "leaflet"
import { useCallback, useEffect, useRef, useState } from "react"
import {
	DEFAULT_MAP_LEVEL,
	getGeoJson,
	type RegionFeature,
	type RegionProperties,
} from "@/geo/util"

type GreeceMapProps = {
	/** GADM administrative level to render (2 = regions, 3 = municipalities) */
	level?: number
	/** Currently placed labels: region_id → label text */
	highlightedRegions?: Map<string, string>
	/** Region IDs that are valid drop targets */
	activeRegionIds?: Set<string>
	/** Validation results: region_id → "correct" | "incorrect" */
	validationMap?: Map<string, "correct" | "incorrect">
	/** Correct answers to reveal after validation: region_id → label */
	correctAnswers?: Map<string, string>
	disabled?: boolean
	onRegionClick?: (regionId: string) => void
}

function getRegionStyle(
	id: string,
	highlightedRegions?: Map<string, string>,
	activeRegionIds?: Set<string>,
	validationMap?: Map<string, "correct" | "incorrect">,
): L.PathOptions {
	const validation = validationMap?.get(id)
	if (validation === "correct") {
		return {
			fillColor: "#86efac",
			fillOpacity: 0.7,
			color: "#16a34a",
			weight: 2,
		}
	}
	if (validation === "incorrect") {
		return {
			fillColor: "#fca5a5",
			fillOpacity: 0.7,
			color: "#dc2626",
			weight: 2,
		}
	}
	if (highlightedRegions?.has(id)) {
		return {
			fillColor: "#93c5fd",
			fillOpacity: 0.5,
			color: "#2563eb",
			weight: 2,
		}
	}
	if (activeRegionIds?.has(id)) {
		return {
			fillColor: "#e0f2fe",
			fillOpacity: 0.4,
			color: "#64748b",
			weight: 1,
		}
	}
	return { fillColor: "#f1f5f9", fillOpacity: 0.6, color: "#94a3b8", weight: 1 }
}

export default function GreeceMap({
	level = DEFAULT_MAP_LEVEL,
	highlightedRegions,
	activeRegionIds,
	validationMap,
	correctAnswers,
	disabled,
	onRegionClick,
}: GreeceMapProps) {
	const containerRef = useRef<HTMLDivElement>(null)
	const mapRef = useRef<L.Map | null>(null)
	const geoLayerRef = useRef<L.GeoJSON | null>(null)
	const propsRef = useRef({
		highlightedRegions,
		activeRegionIds,
		validationMap,
		correctAnswers,
		disabled,
		onRegionClick,
	})
	propsRef.current = {
		highlightedRegions,
		activeRegionIds,
		validationMap,
		correctAnswers,
		disabled,
		onRegionClick,
	}

	const [hasBeenVisible, setHasBeenVisible] = useState(false)

	// Track when the container first becomes visible
	useEffect(() => {
		if (hasBeenVisible) {
			return
		}
		if (!containerRef.current) {
			return
		}
		const el = containerRef.current

		// Check if already visible (for the first/active question)
		if (el.offsetWidth > 0 && el.offsetHeight > 0) {
			setHasBeenVisible(true)
			return
		}

		const observer = new IntersectionObserver(
			(entries) => {
				if (entries[0]?.isIntersecting) {
					setHasBeenVisible(true)
					observer.disconnect()
				}
			},
			{ threshold: 0.01 },
		)
		observer.observe(el)
		return () => observer.disconnect()
	}, [hasBeenVisible])

	// Initialize Leaflet map only after container is visible
	const initMap = useCallback(() => {
		if (!containerRef.current) {
			return
		}
		if (mapRef.current) {
			return
		}

		const map = L.map(containerRef.current, {
			center: [38.5, 24.0],
			zoom: 6,
			zoomControl: true,
			scrollWheelZoom: true,
			dragging: true,
		})

		const geoLayer = L.geoJSON(getGeoJson(level), {
			style: (feature) => {
				const id = feature?.properties?.id ?? ""
				const {
					highlightedRegions: hl,
					activeRegionIds: active,
					validationMap: vm,
				} = propsRef.current
				return getRegionStyle(id, hl, active, vm)
			},
			onEachFeature: (feature, layer) => {
				const props = feature.properties as RegionProperties
				const id = props.id

				layer.on("click", () => {
					const { disabled: d, onRegionClick: onClick } = propsRef.current
					if (d) {
						return
					}
					if (onClick) {
						onClick(id)
					}
				})

				layer.on("mouseover", (e) => {
					const {
						disabled: d,
						activeRegionIds: active,
						onRegionClick: onClick,
					} = propsRef.current
					if (d) {
						return
					}
					if (active?.has(id) || (!active && onClick)) {
						;(e.target as L.Path).setStyle({
							fillColor: "#bfdbfe",
							fillOpacity: 0.6,
							weight: 2,
						})
					}
				})

				layer.on("mouseout", (e) => {
					const {
						highlightedRegions: hl,
						activeRegionIds: active,
						validationMap: vm,
					} = propsRef.current
					const style = getRegionStyle(id, hl, active, vm)
					;(e.target as L.Path).setStyle(style)
				})
			},
		}).addTo(map)

		mapRef.current = map
		geoLayerRef.current = geoLayer

		// Container is guaranteed to be visible at this point
		requestAnimationFrame(() => {
			map.invalidateSize()
			map.fitBounds(geoLayer.getBounds(), { padding: [20, 20] })
		})
	}, [level])

	useEffect(() => {
		if (!hasBeenVisible) {
			return
		}
		initMap()
		return () => {
			if (mapRef.current) {
				mapRef.current.remove()
				mapRef.current = null
				geoLayerRef.current = null
			}
		}
	}, [hasBeenVisible, initMap])

	// Update styles and labels when state changes
	useEffect(() => {
		if (!geoLayerRef.current) {
			return
		}

		geoLayerRef.current.eachLayer((layer) => {
			const feature = (layer as { feature?: RegionFeature }).feature
			if (!feature?.properties?.id) {
				return
			}

			const id = feature.properties.id as string
			const style = getRegionStyle(
				id,
				highlightedRegions,
				activeRegionIds,
				validationMap,
			)
			;(layer as L.Path).setStyle(style)

			// Show placed label or correct answer on the region
			const placed = highlightedRegions?.get(id)
			const correct = correctAnswers?.get(id)
			const validation = validationMap?.get(id)

			// Determine what text to show
			let labelText: string | null = null
			let cssClass = "map-label"
			if (validation === "correct" && placed) {
				labelText = placed
				cssClass = "map-label map-label--correct"
			} else if (validation === "incorrect" && placed && correct) {
				// Show user's wrong answer (struck) + the correct answer
				labelText = `<s>${placed}</s><br><span>${correct}</span>`
				cssClass = "map-label map-label--incorrect"
			} else if (validation === "incorrect" && placed) {
				labelText = placed
				cssClass = "map-label map-label--incorrect"
			} else if (validation === "incorrect" && correct) {
				// Missed region: show what the correct answer is
				labelText = correct
				cssClass = "map-label map-label--correct"
			} else if (placed) {
				labelText = placed
				cssClass = "map-label map-label--placed"
			} else if (correct) {
				labelText = correct
				cssClass = "map-label map-label--correct"
			}

			// Bind/unbind permanent tooltip as label
			const typedLayer = layer as L.Path & {
				getTooltip: () => L.Tooltip | undefined
				unbindTooltip: () => void
				bindTooltip: (content: string, options?: L.TooltipOptions) => void
			}
			if (labelText) {
				// Always rebind so the CSS className is applied to the DOM element
				// (Leaflet ignores options.className changes on existing tooltips)
				if (typedLayer.getTooltip()) {
					typedLayer.unbindTooltip()
				}
				typedLayer.bindTooltip(labelText, {
					permanent: true,
					direction: "center",
					className: cssClass,
				})
			} else {
				if (typedLayer.getTooltip()) {
					typedLayer.unbindTooltip()
				}
			}
		})
	}, [highlightedRegions, activeRegionIds, validationMap, correctAnswers])

	return (
		<div
			ref={containerRef}
			className="h-[400px] w-full overflow-hidden rounded-xl"
			style={{ background: "#f0f9ff" }}
		/>
	)
}
