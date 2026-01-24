export {}

type DjangoMessage = {
	message: string
	level: number
	tags: string
	extra_tags: string
	level_tag: string
}

declare module "@inertiajs/core" {
	export interface InertiaConfig {
		sharedPageProps: {
			messages: DjangoMessage[]
		}
	}
}
