/*
 * MapPointer admin: two fixes to the `areas` picker.
 *
 * 1. Its options must follow the selected map `level` (2 = regions,
 *    3 = municipalities) without a page reload. django-jsonform renders `areas`
 *    from a static `enum` and a `handler` URL baked into the widget schema at
 *    page load, and since `level` is a model field outside the JSON `content`,
 *    the schema can't reference it. So we wrap `reactJsonForm.createForm` to
 *    capture the widget instance and, on `level` change, swap the enum and the
 *    handler's level and re-render via `instance.update({ schema, data })`,
 *    preserving the current answers.
 *
 * 2. The autocomplete widget hides its option list while its search box is
 *    empty, so an editor who has not typed yet has nothing to browse. We seed
 *    the box with a space, which the options endpoint reads as "every area of
 *    this level".
 *
 * Load order (enforced by MapPointerAdminForm.Media): react-json-form.js →
 * THIS FILE → index.js. That lets us wrap createForm before index.js mounts.
 */
;(() => {
	var CONTENT_INPUT_ID = "id_content"
	var SEARCH_INPUT_SELECTOR = ".rjf-autocomplete-field-search input"
	/** Blank query — the endpoint answers it with the level's whole list. */
	var BROWSE_ALL_QUERY = " "

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
				setupBrowseAll()
			})
		} else {
			setupLevelSync(instance)
			setupBrowseAll()
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
			var areaItems = items?.properties?.areas?.items
			if (!areaItems) {
				return
			}
			areaItems.enum = areas
			// The picker searches one level at a time, and the level is the last
			// segment of its options endpoint (".../area-options/<level>/").
			if (areaItems.handler) {
				areaItems.handler = areaItems.handler.replace(
					/\/\d+\/$/,
					`/${levelSelect.value}/`,
				)
			}
			// Preserve whatever the editor currently holds; server-side
			// validation rejects any area not valid for the chosen level.
			instance.update({ schema: schema, data: instance.getData() })
		})
	}

	/** React owns the input's value, so write through the native setter and
	 * dispatch the event React listens for. */
	function setInputValue(input, value) {
		var descriptor = Object.getOwnPropertyDescriptor(
			window.HTMLInputElement.prototype,
			"value",
		)
		descriptor.set.call(input, value)
		input.dispatchEvent(new Event("input", { bubbles: true }))
	}

	function browseAllOptions(input) {
		// Anything the editor typed takes precedence over the whole list.
		if (input.value !== "") {
			return
		}
		setInputValue(input, BROWSE_ALL_QUERY)
	}

	var browseAllReady = false

	function setupBrowseAll() {
		if (browseAllReady) {
			return
		}
		browseAllReady = true

		// The search box mounts and unmounts with the picker's popup, so catch it
		// as it appears rather than looking for it once.
		var observer = new MutationObserver((mutations) => {
			for (const mutation of mutations) {
				for (const node of mutation.addedNodes) {
					if (node.nodeType !== Node.ELEMENT_NODE) {
						continue
					}
					const input = node.matches(SEARCH_INPUT_SELECTOR)
						? node
						: node.querySelector(SEARCH_INPUT_SELECTOR)
					if (input) {
						browseAllOptions(input)
					}
				}
			}
		})
		observer.observe(document.body, { childList: true, subtree: true })

		// Clearing the box means "show everything" too. Re-seeding fires another
		// input event, but by then the value is no longer empty.
		document.body.addEventListener("input", (event) => {
			if (
				event.target instanceof window.HTMLInputElement &&
				event.target.matches(SEARCH_INPUT_SELECTOR)
			) {
				browseAllOptions(event.target)
			}
		})
	}
})()
