const LOG_LEVELS = {
	debug: 0,
	info: 1,
	warn: 2,
	error: 3,
	silent: 4,
} as const

type LogLevel = keyof typeof LOG_LEVELS

function getCurrentLevel(): number {
	const env = (import.meta.env.VITE_LOG_LEVEL as string | undefined)
		?.toLowerCase()
		?.trim() as LogLevel | undefined

	if (env && env in LOG_LEVELS) {
		return LOG_LEVELS[env]
	}

	// Default: debug in dev, warn in production
	return import.meta.env.DEV ? LOG_LEVELS.debug : LOG_LEVELS.warn
}

const level = getCurrentLevel()

function prefix(): string {
	return `[${new Date().toISOString()}]`
}

function shouldLog(target: LogLevel): boolean {
	return LOG_LEVELS[target] >= level
}

export const logger = {
	debug(...args: unknown[]) {
		if (shouldLog("debug")) {
			// biome-ignore lint/suspicious/noConsole: logger is the approved console wrapper
			console.log(prefix(), "[DEBUG]", ...args)
		}
	},
	info(...args: unknown[]) {
		if (shouldLog("info")) {
			// biome-ignore lint/suspicious/noConsole: logger is the approved console wrapper
			console.log(prefix(), "[INFO]", ...args)
		}
	},
	warn(...args: unknown[]) {
		if (shouldLog("warn")) {
			// biome-ignore lint/suspicious/noConsole: logger is the approved console wrapper
			console.warn(prefix(), "[WARN]", ...args)
		}
	},
	error(...args: unknown[]) {
		if (shouldLog("error")) {
			// biome-ignore lint/suspicious/noConsole: logger is the approved console wrapper
			console.error(prefix(), "[ERROR]", ...args)
		}
	},
} as const
