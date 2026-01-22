import type { PropsWithChildren, ReactNode } from "react";

import { Link } from "@inertiajs/react";

const Layout = ({ children }: PropsWithChildren) => (
	<>
		<div>
			<nav className="flex items-start justify-center">
				<ul className="flex space-x-4">
					<li>
						<Link href="/">Home</Link>
					</li>
				</ul>
			</nav>
			<div className="flex items-center justify-center mt-32">{children}</div>
		</div>
	</>
);

export default (page: ReactNode) => <Layout>{page}</Layout>;
