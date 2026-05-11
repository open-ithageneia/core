import type { ValidationStatus } from "@/types/enums"

export type CellValue<T = string> = T | null

export type ValidationState = ValidationStatus | null
