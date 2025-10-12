/**
 * @name MrStrangerVideoLoader
 * @author MrStranger & ChatGPT
 * @version 2.0.0
 * @description Injects the video background. This plugin is required for the theme to work.
 * @source https://github.com/MrStrangerThemes/AnimeEdition
 */

module.exports = class MrStrangerVideoLoader {
  start() {
    // Stop if the video already exists to prevent duplicates
    if (document.getElementById("mrstranger-video-bg")) return;

    const video = document.createElement("video");
    video.id = "mrstranger-video-bg";
    video.src = "https://files.catbox.moe/syas2u.webm";
    video.autoplay = true;
    video.loop = true;
    video.muted = true;
    video.style.cssText = `
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        object-fit: cover !important;
        z-index: -1 !important; /* Places it behind Discord's UI */
        pointer-events: none !important;
        opacity: 0.6 !important; /* Video brightness */
    `;
    document.body.prepend(video);
    video
      .play()
      .catch((err) => console.error("MrStranger VideoLoader Error:", err));
  }

  stop() {
    const video = document.getElementById("mrstranger-video-bg");
    if (video) video.remove();
  }
};
