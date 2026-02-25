// core\frontend\js\test-full\pages\EntryPoint.tsx
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

const Home = () => {
	const navigate = useNavigate()

	return (
		<div className="min-h-screen bg-muted/30 flex items-center justify-center p-6">
			<div className="max-w-4xl w-full space-y-8">
				{/* Εισαγωγή */}
				<Card>
					<CardHeader>
						<CardTitle className="text-2xl">
							Εξετάσεις Ιθαγένειας 2026
						</CardTitle>
					</CardHeader>

					<CardContent className="space-y-4 text-sm text-muted-foreground">
						<p>
							Για την απόκτηση της ελληνικής ιθαγένειας απαιτείται η επιτυχής
							συμμετοχή στις εξετάσεις για το Πιστοποιητικό Επάρκειας Γνώσεων
							για Πολιτογράφηση (ΠΕΓΠ).
						</p>

						<p>
							Οι εξετάσεις διεξάγονται δύο φορές τον χρόνο (Άνοιξη και
							Φθινόπωρο) και περιλαμβάνουν γλωσσική επάρκεια επιπέδου Β1 και
							αξιολόγηση γνώσεων σε βασικές θεματικές ενότητες.
						</p>

						<Separator />

						<div className="space-y-2">
							<p className="font-medium text-foreground">
								Βαθμολογία Επιτυχίας
							</p>
							<ul className="list-disc pl-5 space-y-1">
								<li>70/100 συνολικά</li>
								<li>40/60 στην Ελληνική Γλώσσα (τουλάχιστον)</li>
								<li>20/40 στις υπόλοιπες ενότητες (τουλάχιστον)</li>
							</ul>
						</div>
					</CardContent>
				</Card>

				{/* Ενότητες */}
				<div className="grid md:grid-cols-2 gap-6">
					<Card className="hover:shadow-md transition">
						<CardHeader>
							<CardTitle className="text-lg">
								Κατανόηση Γραπτού Κειμένου
							</CardTitle>
						</CardHeader>

						<CardContent className="space-y-4 text-sm text-muted-foreground">
							<p>Αξιολόγηση γλωσσικής επάρκειας επιπέδου Β1:</p>

							<ul className="list-disc pl-5 space-y-1">
								<li>Κατανόηση κειμένου</li>
								<li>Σύντομες γραπτές απαντήσεις</li>
								<li>Παραγωγή γραπτού λόγου</li>
								<br />
							</ul>

							<Button
								size="lg"
								className="w-full"
								onClick={() => navigate("/language-test-full")}
							>
								Έναρξη Προσομοίωσης
							</Button>
						</CardContent>
					</Card>

					<Card className="hover:shadow-md transition">
						<CardHeader>
							<CardTitle className="text-lg">
								Θεσμοί, Ιστορία, Γεωγραφία, Πολιτισμός
							</CardTitle>
						</CardHeader>

						<CardContent className="space-y-4 text-sm text-muted-foreground">
							<p>Αξιολόγηση γνώσεων σε τέσσερις βασικές ενότητες:</p>

							<ul className="list-disc pl-5 space-y-1">
								<li>Πολιτικοί Θεσμοί</li>
								<li>Ιστορία</li>
								<li>Γεωγραφία</li>
								<li>Πολιτισμός</li>
							</ul>

							<Button
								size="lg"
								className="w-full"
								onClick={() => navigate("/test-full")}
							>
								Έναρξη Προσομοίωσης
							</Button>
						</CardContent>
					</Card>

					<Card className="hover:shadow-md transition">
						<CardHeader>
							<CardTitle className="text-lg">
								Κατανόηση Προφορικού Λόγου
							</CardTitle>
						</CardHeader>

						<CardContent className="space-y-4 text-sm text-muted-foreground">
							<p>Ακουστικό τεστ κατανόησης με επιλογή θέματος.</p>
							<br />

							<Button
								size="lg"
								className="w-full"
								onClick={() => navigate("/audio-test")}
							>
								Έναρξη Προσομοίωσης
							</Button>
						</CardContent>
					</Card>

					<Card className="hover:shadow-md transition">
						<CardHeader>
							<CardTitle className="text-lg">
								Παραγωγή Προφορικού Λόγου
							</CardTitle>
						</CardHeader>

						<CardContent className="space-y-4 text-sm text-muted-foreground">
							<p>
								Θέματα στην ενότητα της Γλώσσας – Παραγωγή Προφορικού Λόγου.
							</p>

							<Button
								size="lg"
								className="w-full"
								onClick={() =>
									window.open(
										"https://exetaseis-ithageneia.ypes.gr/PAPYROS/services/CustomServices/getExamTopic/907931?1771488887281",
										"_blank",
									)
								}
							>
								Προβολή PDF
							</Button>
						</CardContent>
					</Card>
				</div>
			</div>
		</div>
	)
}

export default Home
