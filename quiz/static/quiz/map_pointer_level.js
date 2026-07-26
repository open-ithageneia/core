/*
 * MapPointer admin: make the `area` dropdown options follow the selected
 * map `level` (2 = regions, 3 = municipalities) without a page reload.
 *
 * django-jsonform renders `area` from a static `enum` baked into the widget
 * schema at page load. Since `level` is a model field outside the JSON
 * `content`, the schema can't reference it. So we:
 *   1. wrap `reactJsonForm.createForm` to capture the widget instance, and
 *   2. on `level` change, swap the schema's area enum and re-render via
 *      `instance.update({ schema, data })`, preserving the current answers.
 *
 * Load order (enforced by MapPointerAdminForm.Media): react-json-form.js →
 * THIS FILE → index.js. That lets us wrap createForm before index.js mounts.
 */
;(() => {
	var CONTENT_INPUT_ID = "id_content"

	var rjf = window.reactJsonForm
	if (!rjf || !rjf.createForm || rjf.__mapPointerWrapped) {
		return
	}
	rjf.__mapPointerWrapped = true

	var originalCreateForm = rjf.createForm
	rjf.createForm = function (config) {
		var instance = originalCreateForm.call(this, config)
		if (config && config.dataInputId === CONTENT_INPUT_ID) {
			setupWhenReady(instance)
		}
		return instance
	}

	function setupWhenReady(instance) {
		if (document.readyState === "loading") {
			document.addEventListener("DOMContentLoaded", () => {
				setupLevelSync(instance)
			})
		} else {
			setupLevelSync(instance)
		}
	}

	function setupLevelSync(instance) {
		var levelSelect = document.getElementById("id_level")
		var dataEl = document.getElementById("map-pointer-area-names")
		if (!levelSelect || !dataEl) {
			return
		}

		var areaNamesByLevel
		try {
			areaNamesByLevel = JSON.parse(dataEl.textContent)
		} catch (_e) {
			return
		}

		levelSelect.addEventListener("change", () => {
			var areas = areaNamesByLevel[String(levelSelect.value)] || []
			var schema = JSON.parse(JSON.stringify(instance.getSchema()))
			var items = schema?.properties?.texts?.items
			var areaProp = items?.properties?.area
			if (!areaProp) {
				return
			}
			areaProp.enum = areas
			// Preserve whatever the editor currently holds; server-side
			// validation rejects any area not valid for the chosen level.
			instance.update({ schema: schema, data: instance.getData() })
		})
	}
})()
