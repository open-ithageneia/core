import { Link } from "@inertiajs/react"
import { Button } from "@/components/ui/button"
import { useNav } from "@/hooks/use-nav"

export default function Home() {
	const nav = useNav()

	return (
		<section className="w-full rounded-2xl bg-white p-6 shadow-sm sm:p-8">
			<h1 className="mb-4 text-2xl font-bold sm:text-3xl">Ποιοι είμαστε</h1>

			<p className="mb-6 text-sm leading-7 text-gray-700 sm:text-base">
				Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
				tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim
				veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea
				commodo consequat.
			</p>

			<div className="flex flex-col gap-3 sm:flex-row">
				<Button asChild>
					<Link href={nav.items.simulation.href}>
						{nav.items.simulation.label}
					</Link>
				</Button>

				<Button asChild>
					<Link href={nav.items.training.href}>{nav.items.training.label}</Link>
				</Button>
			</div>
		</section>
	)
}
