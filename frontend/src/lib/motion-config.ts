export const springConfigs = {
  gentle: { type: 'spring' as const, stiffness: 300, damping: 30 },
  snappy: { type: 'spring' as const, stiffness: 400, damping: 25 },
  smooth: { type: 'spring' as const, stiffness: 100, damping: 20 },
  bouncy: { type: 'spring' as const, stiffness: 500, damping: 15 }
};

export const easings = {
  cinematic: [0.22, 1, 0.36, 1] as const,
  standard: [0.4, 0, 0.2, 1] as const,
  emphasized: [0, 0, 0.2, 1] as const
};

export const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
  transition: { duration: 0.4, ease: easings.cinematic }
};
