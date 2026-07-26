import { router } from "@inertiajs/react"
import { Button } from "@/components/ui/button"

type SimulationMode = "knowledge" | "listening"

const MODE_CONFIG: Record<
	SimulationMode,
	{ title: string; description: string }
> = {
	knowledge: {
		title: "Τεστ γνώσεων",
		description:
			"20 τυχαίες ερωτήσεις από όλες τις θεματικές κατηγορίες. Έχετε 30 λεπτά στη διάθεσή σας.",
	},
	listening: {
		title: "Ακουστικό τεστ",
		description:
			"20 τυχαίες ακουστικές ερωτήσεις. Έχετε 30 λεπτά στη διάθεσή σας.",
	},
}

type SimulationMenuProps = {
	modes: { key: SimulationMode; href: string }[]
}

export default function SimulationMenu({ modes }: SimulationMenuProps) {
	return (
		<section className="mx-auto max-w-3xl space-y-4">
			<h1 className="text-2xl font-bold">Τεστ προσομοίωσης</h1>
			<div className="grid gap-4 sm:grid-cols-2">
				{modes.map(({ key, href }) => {
					const config = MODE_CONFIG[key]
					return (
						<div
							key={key}
							className="flex flex-col rounded-2xl bg-white p-6 shadow-sm"
						>
							<h2 className="mb-2 text-xl font-bold">{config.title}</h2>
							<p className="mb-4 flex-1 text-sm text-gray-600">
								{config.description}
							</p>
							<Button
								onClick={() =>
									router.get(href, { start: "1" }, { preserveState: false })
								}
								className="w-full"
							>
								Ξεκινήστε
							</Button>
						</div>
					)
				})}
			</div>
		</section>
	)
}
