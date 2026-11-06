import { useEffect, useRef } from "react";
import { useStage } from "./stage";

export function FlowerVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const { active, still } = useStage();

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (!active || still) {
      video.pause();
      return;
    }

    void video.play().catch(() => {
      // The poster remains visible if the browser declines autoplay.
    });
  }, [active, still]);

  return (
    <div className="v1-flower-video-wrap" aria-hidden>
      <video
        ref={videoRef}
        className="v1-flower-video"
        poster="/variant-1/flower-scene-poster-v2.webp"
        autoPlay={!still}
        loop
        muted
        playsInline
        preload="auto"
        disablePictureInPicture
      >
        <source src="/variant-1/flower-scene-alpha-v2.webm" type="video/webm" />
      </video>
    </div>
  );
}
