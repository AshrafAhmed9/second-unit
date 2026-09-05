/** Renders a real exported render frame (see backlot/export_ui_frames.py and
 * control-room/public/frames/MANIFEST.json for provenance/sha256). Plain
 * <img>, not next/image — the standalone Docker build has no `sharp`, so
 * Next's image optimizer isn't available in the deployed container.
 * imageRendering: pixelated keeps the denoiser fireflies sharp instead of
 * letting the browser blur them into a soft, less convincing smear.
 */
export function FramePanel({
  src,
  alt,
  caption,
  aspect = "16/9",
}: {
  src: string;
  alt: string;
  caption?: string;
  aspect?: string;
}) {
  return (
    <div style={{ position: "relative", background: "#000", aspectRatio: aspect, borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
      <img
        src={src}
        alt={alt}
        width={960}
        height={540}
        style={{ width: "100%", height: "100%", objectFit: "cover", imageRendering: "pixelated", display: "block" }}
      />
      {caption && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            padding: "8px 12px",
            background: "linear-gradient(transparent, rgba(0,0,0,0.75))",
            fontSize: 12,
            color: "#d8dce2",
            fontFamily: "var(--mono)",
          }}
        >
          {caption}
        </div>
      )}
    </div>
  );
}
