"use client";

import Image from "next/image";
import { useEffect, useState } from "react";

import { useHomeBackgroundImageUrls } from "@/hooks/use-home-background-image-urls";

export function HomeBackgroundSlideshow({ imageUrls = [] }: { imageUrls?: string[] }) {
  const resolvedImageUrls = useHomeBackgroundImageUrls(imageUrls);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (resolvedImageUrls.length < 2) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setActiveIndex((currentIndex) => (currentIndex + 1) % resolvedImageUrls.length);
    }, 6000);

    return () => window.clearInterval(intervalId);
  }, [resolvedImageUrls.length]);

  if (resolvedImageUrls.length === 0) {
    return null;
  }

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {resolvedImageUrls.map((imageUrl, index) => {
        const isActive = index === activeIndex;

        return (
          <div
            key={imageUrl}
            className={`home-background-slide absolute inset-0 transition-opacity duration-[1200ms] ease-out ${
              isActive ? "opacity-100" : "opacity-0"
            }`}
          >
            <Image
              alt=""
              aria-hidden="true"
              className={`h-full w-full object-cover ${isActive ? "home-background-zoom-out" : ""}`}
              fill
              priority={index === 0}
              sizes="100vw"
              src={imageUrl}
              unoptimized
            />
          </div>
        );
      })}
    </div>
  );
}
