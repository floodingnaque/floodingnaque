/**
 * WebGL Availability Detection
 *
 * Checks if the browser supports WebGL (required for deck.gl).
 * Computed once at module load time.
 */

export const isWebGLAvailable = (() => {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
})();
