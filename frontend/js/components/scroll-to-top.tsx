import { ArrowUp } from "lucide-react"
import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"

export function ScrollToTop() {
	const [visible, setVisible] = useState(false)

	useEffect(() => {
		const scrollContainer = document.querySelector("[data-scroll-container]")
		if (!scrollContainer) {
			return
		}

		const handleScroll = () => {
			setVisible(scrollContainer.scrollTop > 300)
		}

		scrollContainer.addEventListener("scroll", handleScroll, {
			passive: true,
		})
		return () => scrollContainer.removeEventListener("scroll", handleScroll)
	}, [])

	if (!visible) {
		return null
	}

	return (
		<Button
			variant="outline"
			size="icon"
			className="fixed bottom-4 right-4 z-30 rounded-full shadow-md"
			onClick={() => {
				const scrollContainer = document.querySelector(
					"[data-scroll-container]",
				)
				scrollContainer?.scrollTo({ top: 0, behavior: "smooth" })
			}}
			aria-label="Scroll to top"
		>
			<ArrowUp className="h-5 w-5" />
		</Button>
	)
}
