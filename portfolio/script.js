const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (reduceMotion) {
  document.querySelectorAll('.reveal').forEach((element) => element.classList.add('visible'));
} else {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      entry.target.classList.toggle('visible', entry.isIntersecting);
    }
  }, {
    threshold: 0.06,
    rootMargin: '-8% 0px -8% 0px'
  });

  document.querySelectorAll('.reveal').forEach((element) => observer.observe(element));
}
