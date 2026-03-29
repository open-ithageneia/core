export {}

type DjangoMessage = {
	message: string
	level: number
	tags: string
	extra_tags: string
	level_tag: string
}

type NavItem = {
	key: string
	label: string
	href: string
}

type Nav = {
	items: Record<string, NavItem>
	list: NavItem[]
	current: string
}

declare module "@inertiajs/core" {
	export interface InertiaConfig {
		sharedPageProps: {
			messages: DjangoMessage[]
			nav: Nav
		}
	}
}
