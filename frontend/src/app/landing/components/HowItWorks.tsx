/**
 * HowItWorks Component
 *
 * Three-step visual explanation of the flood prediction pipeline:
 * Collect → Predict → Alert.
 */

import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { CloudRain, Brain, Bell } from 'lucide-react';

const STEPS = [
  {
    num: 1,
    icon: CloudRain,
    title: 'Collect Weather Data',
    desc: 'Real-time weather observations are gathered from PAGASA-Parañaque and OpenWeatherMap - rainfall, humidity, wind speed, cloud cover, tidal levels, and more.',
  },
  {
    num: 2,
    icon: Brain,
    title: 'Predict with ML (Random Forest v6)',
    desc: 'A Random Forest classifier trained on 13,698 samples and 10 engineered features evaluates flood probability for each barangay with 96.75% accuracy.',
  },
  {
    num: 3,
    icon: Bell,
    title: 'Alert in Real-Time',
    desc: 'Each barangay is assigned a risk level - SAFE, ALERT, or CRITICAL - delivered instantly via the dashboard, SSE push, and simulated SMS broadcast.',
  },
] as const;

const container = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.2, delayChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.2 });

  return (
    <section id="how-it-works" className="py-20 sm:py-24 bg-background">
      <div className="container mx-auto px-4" ref={ref}>
        {/* Heading */}
        <div className="text-center mb-14">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-risk-safe mb-3">
            How It Works
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            From Raw Weather Data to Flood Alerts
          </h2>
          <p className="mt-3 text-muted-foreground max-w-xl mx-auto leading-relaxed">
            Three automated steps power every prediction - no manual input required.
          </p>
        </div>

        {/* Steps */}
        <motion.div
          variants={container}
          initial="hidden"
          animate={isInView ? 'show' : undefined}
          className="grid grid-cols-1 md:grid-cols-3 gap-10 max-w-5xl mx-auto"
        >
          {STEPS.map((s) => {
            const Icon = s.icon;
            return (
              <motion.div
                key={s.num}
                variants={item}
                className="flex flex-col items-center text-center space-y-4"
              >
                {/* Numbered circle */}
                <div className="relative">
                  <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center">
                    <Icon className="h-9 w-9 text-primary" />
                  </div>
                  <span className="absolute -top-1 -right-1 h-7 w-7 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center shadow">
                    {s.num}
                  </span>
                </div>

                <h3 className="text-lg font-semibold text-foreground">{s.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">
                  {s.desc}
                </p>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}

export default HowItWorks;
