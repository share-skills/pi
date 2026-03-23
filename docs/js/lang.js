// Language toggle - defaults to English
(function() {
  const STORAGE_KEY = 'pi-lang';

  function setLang(lang) {
    document.documentElement.setAttribute('data-lang', lang);
    localStorage.setItem(STORAGE_KEY, lang);
    // Update toggle button text
    document.querySelectorAll('.lang-toggle').forEach(btn => {
      btn.textContent = lang === 'en' ? '中文' : 'EN';
    });
  }

  function init() {
    const saved = localStorage.getItem(STORAGE_KEY) || 'en';
    setLang(saved);

    document.addEventListener('click', function(e) {
      if (e.target.classList.contains('lang-toggle')) {
        const current = document.documentElement.getAttribute('data-lang') || 'en';
        setLang(current === 'en' ? 'zh' : 'en');
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
