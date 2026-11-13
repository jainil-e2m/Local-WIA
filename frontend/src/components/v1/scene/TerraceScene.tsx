import { useEffect, useRef } from "react";
import { Desk } from "./Desk";
import { useStage } from "./stage";

export function TerraceScene() {
  const { active, still } = useStage();
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (!active || still) video.pause();
    else void video.play().catch(() => { /* Keep the still underneath when autoplay is unavailable. */ });
  }, [active, still]);

  return (
    <div className="v1-terrace-scene" aria-hidden>
      <img className="v1-terrace-extension" src="/variant-1/terrace-extended.webp" alt="" decoding="async" />
      <video
        ref={videoRef}
        className="v1-terrace-video"
        poster="/variant-1/terrace-poster.webp"
        autoPlay={!still}
        loop
        muted
        playsInline
        preload="metadata"
        disablePictureInPicture
      >
        <source src="/variant-1/terrace-breeze.mp4" type="video/mp4" />
      </video>
      <div className="v1-terrace-objects">
        <Desk showBooks={false} terrace />
        <img className="v1-terrace-stationery" src="/variant-1/terrace-stationery-v2.webp" width={1902} height={827} alt="" decoding="async" />
      </div>
    </div>
  );
}
