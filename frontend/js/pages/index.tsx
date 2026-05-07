import { Link } from "@inertiajs/react"
import { Button } from "@/components/ui/button"
import { useNav } from "@/hooks/use-nav"

export default function Home() {
	const nav = useNav()

	return (
		<div className="space-y-4">
			{/* Hero Section */}
			<section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-600 to-indigo-700 px-6 py-12 text-white shadow-xl sm:px-12 sm:py-16">
				<div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0djItSDJ2LTJoMzR6bTAtMzBWMkgydjJoMzR6TTIgMmgzNHYySDJ6Ii8+PC9nPjwvZz48L3N2Zz4=')] opacity-30" />
				<div className="relative z-10 max-w-4xl">
					<h1 className="mb-4 text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl">
						Open Ithageneia
					</h1>
					<p className="mb-8 text-base leading-relaxed text-blue-100 sm:text-lg">
						Δωρεάν εφαρμογή προετοιμασίας για τις εξετάσεις απόκτησης ελληνικής
						ιθαγένειας.
					</p>
					<div className="flex flex-col gap-3 sm:flex-row">
						<Button
							asChild
							size="lg"
							variant="secondary"
							className="font-semibold"
						>
							<Link href={nav.items.simulation.href}>
								{nav.items.simulation.label}
							</Link>
						</Button>
					</div>
				</div>
			</section>

			{/* About Section */}
			<section className="rounded-2xl border bg-white p-6 shadow-sm sm:p-8">
				<h2 className="mb-4 text-xl font-bold sm:text-2xl">Ποιοι είμαστε</h2>
				<div className="space-y-4 text-sm leading-7 text-gray-700 sm:text-base">
					<p>
						Η εφαρμογή open-ithegeneia φτιάχτηκε από μια ομάδα
						προγραμματιστών/πληροφορικάριων. Σκοπός της είναι να λειτουργήσει ως
						βοήθημα των αλληλέγγυων μαθημάτων προετοιμασίας για τις εξετάσεις
						απόκτησης ελληνικής ιθαγένειας που οργανώνονται συλλογικά από τα
						Πίσω Θρανία.
					</p>
					<p>
						Πίσω Θρανία, ως κομμάτι του Στεκιού Μεταναστών Αθήνας, αποτελούν μία
						πρωτοβουλία από τα κάτω με στόχο την δωρεάν παροχή μαθημάτων
						εκμάθησης της ελληνικής γλώσσας σε ενήλικες μετανάστες/τριες και
						πρόσφυγες/γισσες. Παράλληλα, στοχεύουν στην έμπρακτη στήριξη και
						αλληλεγγύη μεταξύ μεταναστών/τριων και ντόπιων και στην ανάπτυξη
						μίας ανθρώπινης κοινότητας χωρίς διακρίσεις.
					</p>
					<p>
						Η εφαρμογή αυτή επιλέγεται να είναι ανοιχτή και δωρεάν σε
						όλους/όλες/α με στόχο να την μοιραστούν όσο το δυνατόν πιο πολλοί
						και πολλές γίνεται.
					</p>
				</div>
			</section>
		</div>
	)
}
