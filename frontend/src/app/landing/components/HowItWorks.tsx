/**
 * HowItWorks Component
 *
 * Three-step visual explanation of the flood prediction pipeline:
 * Collect → Predict → Alert.
 */

import { motion, useInView } from "framer-motion";
import { Bell, Brain, CloudRain } from "lucide-react";
import { useRef } from "react";

const STEPS = [
  {
    num: 1,
    icon: CloudRain,
    title: "Collect Weather Data",
    desc: "Real-time weather observations are gathered from PAGASA-Parañaque and OpenWeatherMap - rainfall, humidity, wind speed, cloud cover, tidal levels, and more.",
  },
  {
    num: 2,
    icon: Brain,
    title: "Predict with ML (Random Forest v6)",
    desc: "A Random Forest classifier trained on 6,570 samples and 13 engineered features evaluates flood probability for each barangay with 97.35% accuracy.",
  },
  {
    num: 3,
    icon: Bell,
    title: "Alert in Real-Time",
    desc: "Each barangay is assigned a risk level - SAFE, ALERT, or CRITICAL - delivered instantly via the dashboard, SSE push, and simulated SMS broadcast.",
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
      <div className="container px-4 mx-auto" ref={ref}>
        {/* Heading */}
        <div className="text-center mb-14">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-risk-safe mb-3">
            How It Works
          </p>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl text-foreground">
            From Raw Weather Data to Flood Alerts
          </h2>
          <p className="max-w-xl mx-auto mt-3 leading-relaxed text-muted-foreground">
            Three automated steps power every prediction - no manual input
            required.
          </p>
        </div>

        {/* Steps */}
        <motion.div
          variants={container}
          initial="hidden"
          animate={isInView ? "show" : undefined}
          className="grid max-w-5xl grid-cols-1 gap-10 mx-auto md:grid-cols-3"
        >
          {STEPS.map((s) => {
            const Icon = s.icon;
            return (
              <motion.div
                key={s.num}
                variants={item}
                className="flex flex-col items-center space-y-4 text-center"
              >
                {/* Numbered circle */}
                <div className="relative">
                  <div className="flex items-center justify-center w-20 h-20 rounded-full bg-primary/10">
                    <Icon className="h-9 w-9 text-primary" />
                  </div>
                  <span className="absolute flex items-center justify-center text-xs font-bold text-white rounded-full shadow -top-1 -right-1 h-7 w-7 bg-primary">
                    {s.num}
                  </span>
                </div>

                <h3 className="text-lg font-semibold text-foreground">
                  {s.title}
                </h3>
                <p className="max-w-xs text-sm leading-relaxed text-muted-foreground">
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
