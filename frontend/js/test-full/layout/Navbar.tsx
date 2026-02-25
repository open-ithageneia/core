// core\frontend\js\test-full\layout\Navbar.tsx
import { Menu, X } from "lucide-react"
import { useState } from "react"
import { NavLink } from "react-router-dom"
import { Button } from "@/components/ui/button"

const Navbar = () => {
	const [open, setOpen] = useState(false)

	return (
		<nav className="border-b bg-background">
			<div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
				<div className="font-semibold text-lg">ΠΕΓΠ</div>

				{/* Desktop menu */}
				<div className="hidden md:flex gap-3">
					<NavItem to="/" label="Αρχική" />
					<NavItem to="/language-test-full" label="Κατανόηση Γλώσσας" />
					<NavItem to="/test-full" label="Γνώσεων" />
					<NavItem to="/audio-test" label="Ακουστικό" />
				</div>

				{/* Hamburger button */}
				<button
					type="button"
					className="md:hidden"
					onClick={() => setOpen((prev) => !prev)}
				>
					{open ? <X size={22} /> : <Menu size={22} />}
				</button>
			</div>

			{/* Mobile menu */}
			{open && (
				<div className="md:hidden px-4 pb-4 flex flex-col gap-3">
					<NavItem to="/" label="Αρχική" onClick={() => setOpen(false)} />
					<NavItem
						to="/language-test-full"
						label="Κατανόηση Γλώσσας"
						onClick={() => setOpen(false)}
					/>
					<NavItem
						to="/test-full"
						label="Γνώσεων"
						onClick={() => setOpen(false)}
					/>
					<NavItem
						to="/audio-test"
						label="Ακουστικό"
						onClick={() => setOpen(false)}
					/>
				</div>
			)}
		</nav>
	)
}

type NavItemProps = {
	to: string
	label: string
	onClick?: () => void
}

const NavItem = ({ to, label, onClick }: NavItemProps) => {
	return (
		<NavLink to={to} onClick={onClick}>
			{({ isActive }) => (
				<Button
					variant={isActive ? "default" : "ghost"}
					className="w-full md:w-auto"
				>
					{label}
				</Button>
			)}
		</NavLink>
	)
}

export default Navbar
