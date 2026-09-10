(() => {
  const body = document.body;
  const theme = document.getElementById('theme');
  const menu = document.getElementById('menu');
  const mobileNav = document.getElementById('mobileNav');
  const saved = localStorage.getItem('engaz-theme');
  if (saved === 'dark') body.classList.add('dark');
  theme?.addEventListener('click', () => {
    body.classList.toggle('dark');
    localStorage.setItem('engaz-theme', body.classList.contains('dark') ? 'dark' : 'light');
  });
  menu?.addEventListener('click', () => mobileNav?.classList.toggle('open'));
  mobileNav?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => mobileNav.classList.remove('open')));
})();
