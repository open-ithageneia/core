import "vite/modulepreload-polyfill"
import { createInertiaApp } from "@inertiajs/react"
import axios from "axios"
import type { ComponentType, ReactElement, ReactNode } from "react"
import { createRoot } from "react-dom/client"
import Layout from "./components/Layout"

import "../css/main.css"

type SharedProps = Record<string, unknown>

type LayoutRenderer = (page: ReactElement) => ReactNode

type InertiaPageComponent = ComponentType<SharedProps> & {
	layout?: LayoutRenderer
}

type PageModule = {
	default: InertiaPageComponent
}

const pages = import.meta.glob<PageModule>("./pages/**/*.tsx")

document.addEventListener("DOMContentLoaded", () => {
	axios.defaults.xsrfCookieName = "csrftoken"
	axios.defaults.xsrfHeaderName = "X-CSRFToken"

	createInertiaApp({
		resolve: async (name) => {
			const importPage = pages[`./pages/${name}.tsx`]
			if (!importPage) {
				throw new Error(`Page not found: ${name}`)
			}

			const { default: Page } = await importPage()
			Page.layout = Page.layout ?? Layout
			return Page
		},
		setup({ el, App, props }) {
			if (!el) return
			createRoot(el).render(<App {...props} />)
		},
	})
})
