// Fade story sections in as they enter the viewport.
const obs = new IntersectionObserver(
  entries => entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add("visible");
      obs.unobserve(e.target);
    }
  }),
  { threshold: 0.15 }
);
document.querySelectorAll(".story").forEach(el => obs.observe(el));
