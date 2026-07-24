/**
 * Geo utilities for the MapPointer quiz type.
 *
 * Backed by boundary data for Greece at several administrative levels:
 *   - level 1 → decentralized administrations (αποκεντρωμένες διοικήσεις)
 *   - level 2 → regions (περιφέρειες)
 *   - level 3 → prefecture units (νομοί / νησιά)
 *   - level 4 → municipalities (δήμοι)
 *   - level 5 → geographic departments (γεωγραφικά διαμερίσματα)
 *
 * With Leaflet handling projection, this module only normalises the raw GADM
 * properties into a small, stable shape and serves the right level on demand.
 */

import gadmLevel1 from "@/geo/data/gadm41_GRC_1.json"
import gadmLevel2 from "@/geo/data/gadm41_GRC_2.json"
import gadmLevel3 from "@/geo/data/gadm41_GRC_3.json"
import geographicDepartments from "@/geo/data/greece_geographic_departments.json"
import prefectureUnits from "@/geo/data/greece_prefecture_units.json"
import type { FeatureCollection, Feature, Geometry } from "geojson"

// ── Types ────────────────────────────────────────────────────────────────────
export interface RegionProperties {
	/** Greek area name, used for answer matching */
	name: string
	/** Latin area name */
	name_latin: string
	/** Stable unique region id (GADM GID_{level}) */
	id: string
}

export type RegionFeature = Feature<Geometry, RegionProperties>

/** Default level used when a question does not specify one. */
export const DEFAULT_MAP_LEVEL = 4

// ── Process GeoJSON ────────────────────────────────────────────────────────
// Each source file uses different property keys for the Greek name, Latin
// name and id, so map them into our compact { name, name_latin, id } shape.
// Keys must stay in sync with quiz/schemas.py MAP_LEVEL_SOURCES.
type SourceKeys = { nameKey: string; latinKey: string; idKey: string }

function processLevel(
	fc: FeatureCollection,
	{ nameKey, latinKey, idKey }: SourceKeys,
): FeatureCollection<Geometry, RegionProperties> {
	return {
		type: "FeatureCollection",
		features: fc.features.map((feature) => {
			const props = feature.properties as Record<string, string>
			return {
				...feature,
				properties: {
					name: props[nameKey],
					name_latin: props[latinKey],
					id: props[idKey],
				},
			} as RegionFeature
		}),
	}
}

const GEOJSON_BY_LEVEL: Record<
	number,
	FeatureCollection<Geometry, RegionProperties>
> = {
	// 1 — decentralized administrations (αποκεντρωμένες διοικήσεις), GADM level 1.
	1: processLevel(gadmLevel1 as FeatureCollection, {
		nameKey: "NL_NAME_1",
		latinKey: "NAME_1",
		idKey: "GID_1",
	}),
	// 2 — regions (περιφέρειες), GADM level 2.
	2: processLevel(gadmLevel2 as FeatureCollection, {
		nameKey: "NL_NAME_2",
		latinKey: "NAME_2",
		idKey: "GID_2",
	}),
	// 3 — prefecture units (νομοί/νησιά): name_greek is Greek, name is Latin.
	3: processLevel(prefectureUnits as FeatureCollection, {
		nameKey: "name_greek",
		latinKey: "name",
		idKey: "id",
	}),
	// 4 — municipalities (δήμοι), GADM level 3.
	4: processLevel(gadmLevel3 as FeatureCollection, {
		nameKey: "NL_NAME_3",
		latinKey: "NAME_3",
		idKey: "GID_3",
	}),
	// 5 — geographic departments (γεωγραφικά διαμερίσματα), derived from
	// prefecture units (see geo/build_geographic_departments.py).
	5: processLevel(geographicDepartments as FeatureCollection, {
		nameKey: "name",
		latinKey: "name_latin",
		idKey: "id",
	}),
}

/** Get the processed GeoJSON for the given map level (falls back to default). */
export function getGeoJson(
	level: number = DEFAULT_MAP_LEVEL,
): FeatureCollection<Geometry, RegionProperties> {
	return GEOJSON_BY_LEVEL[level] ?? GEOJSON_BY_LEVEL[DEFAULT_MAP_LEVEL]
}

/** Get all available region IDs for the given level */
export function getAllRegionIds(level: number = DEFAULT_MAP_LEVEL): string[] {
	return getGeoJson(level).features.map((f) => f.properties.id)
}

/** Look up a feature by region ID within the given level */
export function getRegionById(
	id: string,
	level: number = DEFAULT_MAP_LEVEL,
): RegionFeature | undefined {
	return getGeoJson(level).features.find((f) => f.properties.id === id)
}
