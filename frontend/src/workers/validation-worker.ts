/**
 * Validation Worker
 *
 * Offloads Zod schema validation for large payloads (bulk alert
 * arrays, weather history) from the main thread.
 */

import { expose } from "comlink";

/**
 * Lightweight validation: checks that required fields exist and
 * have the correct types. This avoids shipping the full Zod library
 * into the worker bundle while still catching malformed data.
 */

interface ValidationError {
  index: number;
  field: string;
  message: string;
}

interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  validCount: number;
  invalidCount: number;
}

/**
 * Validate an array of prediction responses.
 */
function validatePredictions(data: unknown[]): ValidationResult {
  const errors: ValidationError[] = [];
  let validCount = 0;

  for (let i = 0; i < data.length; i++) {
    const item = data[i];
    if (!item || typeof item !== "object") {
      errors.push({ index: i, field: "root", message: "Expected an object" });
      continue;
    }

    const record = item as Record<string, unknown>;

    if (typeof record["prediction"] !== "number") {
      errors.push({
        index: i,
        field: "prediction",
        message: "Missing or non-numeric prediction",
      });
    }
    if (typeof record["risk_level"] !== "number") {
      errors.push({
        index: i,
        field: "risk_level",
        message: "Missing or non-numeric risk_level",
      });
    }
    if (typeof record["confidence"] !== "number") {
      errors.push({
        index: i,
        field: "confidence",
        message: "Missing or non-numeric confidence",
      });
    }

    if (!errors.some((e) => e.index === i)) {
      validCount++;
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    validCount,
    invalidCount: data.length - validCount,
  };
}

/**
 * Validate an array of alert objects.
 */
function validateAlerts(data: unknown[]): ValidationResult {
  const errors: ValidationError[] = [];
  let validCount = 0;

  for (let i = 0; i < data.length; i++) {
    const item = data[i];
    if (!item || typeof item !== "object") {
      errors.push({ index: i, field: "root", message: "Expected an object" });
      continue;
    }

    const record = item as Record<string, unknown>;

    if (typeof record["id"] !== "number") {
      errors.push({
        index: i,
        field: "id",
        message: "Missing or non-numeric id",
      });
    }
    if (typeof record["risk_level"] !== "number") {
      errors.push({
        index: i,
        field: "risk_level",
        message: "Missing or non-numeric risk_level",
      });
    }
    if (typeof record["message"] !== "string") {
      errors.push({
        index: i,
        field: "message",
        message: "Missing or non-string message",
      });
    }

    if (!errors.some((e) => e.index === i)) {
      validCount++;
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    validCount,
    invalidCount: data.length - validCount,
  };
}

const validationWorkerApi = {
  validatePredictions,
  validateAlerts,
};

export type ValidationWorkerApi = typeof validationWorkerApi;

expose(validationWorkerApi);
