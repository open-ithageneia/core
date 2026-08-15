import L from "leaflet"
import { useCallback, useEffect, useRef, useState } from "react"
import {
	DEFAULT_MAP_LEVEL,
	getGeoJson,
	type RegionFeature,
	type RegionProperties,
} from "@/geo/util"

/**
 * Per-region outcome after validation. ``alternative`` marks a region that
 * would also have been accepted for an answer already given elsewhere — an
 * answer can span several regions, and only one of them was ever needed.
 */
export type RegionValidation = "correct" | "incorrect" | "alternative"

/**
 * One label drawn on a region. A region carries a list of them rather than a
 * single string: answers may share a polygon, so several labels can be placed
 * on — or revealed for — the same region.
 */
export type RegionLabel = {
	text: string
	/** Visual treatment; ``placed`` is the plain blue chip shown before validation. */
	state: "placed" | RegionValidation
	/** Strike the text through, for a wrong answer shown beside the right one. */
	struck?: boolean
}

type GreeceMapProps = {
	/** Map level to render (see MapLevel; 2 = regions, 4 = municipalities/islands) */
	level?: number
	/** Labels to draw on each region: region_id → labels, top to bottom */
	regionLabels?: Map<string, RegionLabel[]>
	/** Region IDs that are valid drop targets */
	activeRegionIds?: Set<string>
	/** Validation results: region_id → outcome */
	validationMap?: Map<string, RegionValidation>
	disabled?: boolean
	onRegionClick?: (regionId: string) => void
}

/** Escape text interpolated into the tooltip's HTML. */
function escapeHtml(text: string): string {
	return text
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
}

/** Render a region's labels as a stack of individually styled chips. */
function renderLabels(labels: RegionLabel[]): string {
	return labels
		.map((label) => {
			const classes = ["map-label__item", `map-label__item--${label.state}`]
			if (label.struck) {
				classes.push("map-label__item--struck")
			}
			return `<span class="${classes.join(" ")}">${escapeHtml(label.text)}</span>`
		})
		.join("")
}

/** Regions holding a not-yet-validated placement, which paints them blue. */
function hasPlacedLabel(
	id: string,
	regionLabels?: Map<string, RegionLabel[]>,
): boolean {
	return (
		regionLabels?.get(id)?.some((label) => label.state === "placed") ?? false
	)
}

function getRegionStyle(
	id: string,
	regionLabels?: Map<string, RegionLabel[]>,
	activeRegionIds?: Set<string>,
	validationMap?: Map<string, RegionValidation>,
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
	if (validation === "alternative") {
		// Light blue, dashed: also acceptable, neither scored nor a mistake.
		return {
			fillColor: "#bfdbfe",
			fillOpacity: 0.6,
			color: "#3b82f6",
			weight: 2,
			dashArray: "4 3",
		}
	}
	if (hasPlacedLabel(id, regionLabels)) {
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
	regionLabels,
	activeRegionIds,
	validationMap,
	disabled,
	onRegionClick,
}: GreeceMapProps) {
	const containerRef = useRef<HTMLDivElement>(null)
	const mapRef = useRef<L.Map | null>(null)
	const geoLayerRef = useRef<L.GeoJSON | null>(null)
	const propsRef = useRef({
		regionLabels,
		activeRegionIds,
		validationMap,
		disabled,
		onRegionClick,
	})
	propsRef.current = {
		regionLabels,
		activeRegionIds,
		validationMap,
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
					regionLabels: labels,
					activeRegionIds: active,
					validationMap: vm,
				} = propsRef.current
				return getRegionStyle(id, labels, active, vm)
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
						regionLabels: labels,
						activeRegionIds: active,
						validationMap: vm,
					} = propsRef.current
					const style = getRegionStyle(id, labels, active, vm)
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
				regionLabels,
				activeRegionIds,
				validationMap,
			)
			;(layer as L.Path).setStyle(style)

			// Every label the region carries, stacked — each paints itself, so a
			// shared polygon can show a correct and a wrong answer side by side.
			const labels = regionLabels?.get(id) ?? []

			// Bind/unbind permanent tooltip as label
			const typedLayer = layer as L.Path & {
				getTooltip: () => L.Tooltip | undefined
				unbindTooltip: () => void
				bindTooltip: (content: string, options?: L.TooltipOptions) => void
			}
			if (labels.length > 0) {
				// Always rebind so the CSS className is applied to the DOM element
				// (Leaflet ignores options.className changes on existing tooltips)
				if (typedLayer.getTooltip()) {
					typedLayer.unbindTooltip()
				}
				typedLayer.bindTooltip(renderLabels(labels), {
					permanent: true,
					direction: "center",
					className: "map-label",
				})
			} else {
				if (typedLayer.getTooltip()) {
					typedLayer.unbindTooltip()
				}
			}
		})
	}, [regionLabels, activeRegionIds, validationMap])

	return (
		<div
			ref={containerRef}
			className="h-[400px] w-full overflow-hidden rounded-xl"
			style={{ background: "#f0f9ff" }}
		/>
	)
}
