import { Link } from "@inertiajs/react"
import { Menu } from "lucide-react"
import type { PropsWithChildren, ReactElement } from "react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { useNav } from "@/hooks/use-nav"

const Layout = ({ children }: PropsWithChildren) => {
	const nav = useNav()
	const isActive = (key: string) => nav.current === key

	return (
		<div className="flex h-dvh flex-col bg-gray-50 text-gray-900">
			<header className="shrink-0 border-b bg-white">
				<div className="mx-auto flex max-w-6xl items-center justify-between px-2 py-2">
					<Link href={nav.items.home.href} className="text-lg font-semibold">
						Open Ithageneia
					</Link>

					<nav className="hidden md:block">
						<ul className="flex items-center gap-3">
							{nav.list.map((item) => (
								<li key={item.key}>
									<Link
										href={item.href}
										className={
											isActive(item.key)
												? "text-sm font-semibold text-black"
												: "text-sm font-medium text-gray-700 transition hover:text-black"
										}
									>
										{item.label}
									</Link>
								</li>
							))}
						</ul>
					</nav>

					<div className="md:hidden">
						<Sheet>
							<SheetTrigger asChild>
								<Button
									variant="outline"
									size="icon"
									aria-label="Toggle navigation menu"
								>
									<Menu className="h-5 w-5" />
								</Button>
							</SheetTrigger>

							<SheetContent side="right">
								<nav className="mt-6">
									<ul className="flex flex-col gap-3">
										{nav.list.map((item) => (
											<li key={item.key}>
												<Link
													href={item.href}
													className={
														isActive(item.key)
															? "block rounded-md bg-gray-100 px-2 py-2 text-sm font-semibold text-black"
															: "block rounded-md px-2 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
													}
												>
													{item.label}
												</Link>
											</li>
										))}
									</ul>
								</nav>
							</SheetContent>
						</Sheet>
					</div>
				</div>
			</header>

			<main className="mx-auto w-full max-w-6xl flex-1 overflow-y-auto px-1 py-1 md:py-2">
				{children}
			</main>
		</div>
	)
}

export default (page: ReactElement) => <Layout>{page}</Layout>
