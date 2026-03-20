/**
 * Shared Motion Variants
 *
 * Framer-motion animation presets matching the landing-page design language.
 * Import these in any page to get consistent entrance animations.
 */

/** Fade up – single element */
export const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45 } },
};

/** Stagger container – wraps a list of fadeUp children */
export const staggerContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1, delayChildren: 0.05 } },
};

/** Fade in – no vertical movement */
export const fadeIn = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.4 } },
};

/** Scale up – good for badges / hero elements */
export const scaleUp = {
  hidden: { opacity: 0, scale: 0.9 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.35, type: "spring" },
  },
};
