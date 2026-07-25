/**
 * PAC — Risk Level Utilities
 * Maps numeric scores and string labels to PAC visual system.
 */

import type { RiskLevel, CrimeSeverity, CrimeStatus } from "@/types/api.types";

// ── Numeric score → RiskLevel ─────────────────────────────────────────────────
export function scoreToRiskLevel(score: number): RiskLevel {
  if (score >= 0.8) return "CRITICAL";
  if (score >= 0.6) return "HIGH";
  if (score >= 0.3) return "MODERATE";
  return "LOW";
}

// ── RiskLevel → Tailwind text colour class ────────────────────────────────────
export function riskLevelToTextClass(level: RiskLevel | string): string {
  switch (level) {
    case "CRITICAL": return "text-[#f85149]";
    case "HIGH":     return "text-[#e98d30]";
    case "MODERATE": return "text-[#d29922]";
    case "LOW":      return "text-[#3fb950]";
    default:         return "text-text-muted";
  }
}

// ── RiskLevel → background CSS class ─────────────────────────────────────────
export function riskLevelToBgClass(level: RiskLevel | string): string {
  switch (level) {
    case "CRITICAL": return "risk-bg-critical";
    case "HIGH":     return "risk-bg-high";
    case "MODERATE": return "risk-bg-moderate";
    case "LOW":      return "risk-bg-low";
    default:         return "bg-bg-elevated";
  }
}

// ── RiskLevel → hex colour ────────────────────────────────────────────────────
export function riskLevelToHex(level: RiskLevel | string): string {
  switch (level) {
    case "CRITICAL": return "#f85149";
    case "HIGH":     return "#e98d30";
    case "MODERATE": return "#d29922";
    case "LOW":      return "#3fb950";
    default:         return "#8b949e";
  }
}

// ── CrimeSeverity → RiskLevel ─────────────────────────────────────────────────
export function severityToRiskLevel(severity: CrimeSeverity): RiskLevel {
  switch (severity) {
    case "critical": return "CRITICAL";
    case "high":     return "HIGH";
    case "medium":   return "MODERATE";
    case "low":      return "LOW";
  }
}

// ── CrimeStatus → display colour ─────────────────────────────────────────────
export function statusToTextClass(status: CrimeStatus): string {
  switch (status) {
    case "registered":          return "text-info-DEFAULT";
    case "under_investigation": return "text-[#d29922]";
    case "chargesheeted":       return "text-[#bc8cff]";
    case "solved":              return "text-[#3fb950]";
    case "closed":              return "text-text-muted";
  }
}

// ── Confidence score → label ──────────────────────────────────────────────────
export function confidenceToLabel(score: number): string {
  if (score >= 0.9) return "Very High";
  if (score >= 0.7) return "High";
  if (score >= 0.5) return "Moderate";
  if (score >= 0.3) return "Low";
  return "Very Low";
}

// ── Confidence score → hex colour ─────────────────────────────────────────────
export function confidenceToColour(score: number): string {
  if (score >= 0.7) return "#3fb950";
  if (score >= 0.5) return "#d29922";
  return "#f85149";
}

// ── Score → percentage string ─────────────────────────────────────────────────
export function scoreToPercent(score: number, decimals = 0): string {
  return `${(score * 100).toFixed(decimals)}%`;
}
