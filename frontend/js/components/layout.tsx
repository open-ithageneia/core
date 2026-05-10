import { Link } from "@inertiajs/react"
import { Menu } from "lucide-react"
import { type PropsWithChildren, type ReactElement, useState } from "react"
import { ScrollToTop } from "@/components/scroll-to-top"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { useNav } from "@/hooks/use-nav"

const Layout = ({ children }: PropsWithChildren) => {
	const nav = useNav()
	const isActive = (key: string) => nav.current === key
	const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

	return (
		<div className="flex h-dvh flex-col bg-gray-50 text-gray-900">
			<header className="shrink-0 border-b bg-white">
				<div className="mx-auto flex h-12 max-w-6xl items-center justify-between px-2">
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
						<Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
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
													onClick={() => setMobileMenuOpen(false)}
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

			<div
				className="flex min-h-0 flex-1 flex-col overflow-y-auto"
				data-scroll-container
			>
				<main className="mx-auto flex min-h-0 w-full max-w-6xl flex-1 flex-col px-1 py-1 md:py-2">
					{children}

					{nav.current === "home" && (
						<footer className="mt-8 border-t bg-white py-4">
							<div className="mx-auto max-w-6xl px-4 text-center text-sm text-gray-500">
								<p>
									Για περισσότερες πληροφορίες σχετικά με τα αλληλέγγυα μαθήματα
									ιθαγένειας μπορείτε να απευθυνθείτε στο mail:{" "}
									<a
										href="mailto:ithageneia.stekimetanaston@gmail.com"
										className="underline hover:text-gray-700"
									>
										ithageneia.stekimetanaston@gmail.com
									</a>
								</p>
							</div>
						</footer>
					)}
				</main>

			</div>
			<ScrollToTop />
		</div>
	)
}

export default (page: ReactElement) => <Layout>{page}</Layout>
