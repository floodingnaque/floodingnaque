/**
 * Temperature Conversion Utilities
 *
 * Provides functions for converting between Celsius and Kelvin,
 * with formatted output for display purposes.
 */

/**
 * Kelvin offset constant (0°C = 273.15K)
 */
const KELVIN_OFFSET = 273.15;

/**
 * Convert Celsius to Kelvin
 *
 * @param celsius - Temperature in Celsius
 * @returns Temperature in Kelvin
 *
 * @example
 * celsiusToKelvin(25) // 298.15
 * celsiusToKelvin(0)  // 273.15
 */
export function celsiusToKelvin(celsius: number): number {
  return celsius + KELVIN_OFFSET;
}

/**
 * Convert Kelvin to Celsius
 *
 * @param kelvin - Temperature in Kelvin
 * @returns Temperature in Celsius
 *
 * @example
 * kelvinToCelsius(298.15) // 25
 * kelvinToCelsius(273.15) // 0
 */
export function kelvinToCelsius(kelvin: number): number {
  return kelvin - KELVIN_OFFSET;
}

/**
 * Format temperature for display
 *
 * @param kelvin - Temperature in Kelvin
 * @param unit - Output unit ('C' for Celsius, 'K' for Kelvin)
 * @returns Formatted temperature string (e.g., "25.5°C" or "298.7K")
 *
 * @example
 * formatTemperature(298.15, 'C') // "25.0°C"
 * formatTemperature(298.15, 'K') // "298.2K"
 */
export function formatTemperature(kelvin: number, unit: 'C' | 'K' = 'C'): string {
  if (unit === 'K') {
    return `${kelvin.toFixed(1)}K`;
  }

  const celsius = kelvinToCelsius(kelvin);
  return `${celsius.toFixed(1)}°C`;
}
