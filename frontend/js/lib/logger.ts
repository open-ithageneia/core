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

	if (env && env in LOG_LEVELS) return LOG_LEVELS[env]

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
		// biome-ignore lint/suspicious/noConsole: logger is the approved console wrapper
		if (shouldLog("debug")) console.log(prefix(), "[DEBUG]", ...args)
	},
	info(...args: unknown[]) {
		// biome-ignore lint/suspicious/noConsole: logger is the approved console wrapper
		if (shouldLog("info")) console.log(prefix(), "[INFO]", ...args)
	},
	warn(...args: unknown[]) {
		// biome-ignore lint/suspicious/noConsole: logger is the approved console wrapper
		if (shouldLog("warn")) console.warn(prefix(), "[WARN]", ...args)
	},
	error(...args: unknown[]) {
		// biome-ignore lint/suspicious/noConsole: logger is the approved console wrapper
		if (shouldLog("error")) console.error(prefix(), "[ERROR]", ...args)
	},
} as const
