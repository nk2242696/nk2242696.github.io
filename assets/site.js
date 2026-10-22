(function () {
  'use strict';

  var systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
  var explicitTheme = false;
  try {
    var storedTheme = localStorage.getItem('theme');
    explicitTheme = storedTheme === 'light' || storedTheme === 'dark';
  } catch (error) {
    console.warn('Could not read the saved theme preference.', error);
  }

  var themeToggle = document.getElementById('themeToggle');
  function syncTheme() {
    if (!themeToggle) return;
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    themeToggle.setAttribute('aria-pressed', String(isDark));
    themeToggle.setAttribute('aria-label', isDark ? 'Switch to light theme' : 'Switch to dark theme');
  }

  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      explicitTheme = true;
      document.documentElement.setAttribute('data-theme', next);
      try {
        localStorage.setItem('theme', next);
      } catch (error) {
        console.warn('Could not save the theme preference.', error);
      }
      syncTheme();
    });
    syncTheme();
  }

  systemTheme.addEventListener('change', function (event) {
    if (!explicitTheme) {
      document.documentElement.setAttribute('data-theme', event.matches ? 'dark' : 'light');
      syncTheme();
    }
  });

  var year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();

  var nav = document.getElementById('navbar');
  if (nav) {
    var onScroll = function () {
      nav.classList.toggle('scrolled', window.scrollY > 50);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    var menuToggle = document.getElementById('menuToggle');
    var navLinks = document.getElementById('primary-navigation');
    var compactNav = window.matchMedia('(max-width: 1100px)');

    function closeMenu(returnFocus) {
      nav.classList.remove('menu-open');
      menuToggle.setAttribute('aria-expanded', 'false');
      menuToggle.querySelector('span').textContent = 'Menu';
      if (returnFocus) menuToggle.focus();
    }

    menuToggle.addEventListener('click', function () {
      var open = menuToggle.getAttribute('aria-expanded') !== 'true';
      nav.classList.toggle('menu-open', open);
      menuToggle.setAttribute('aria-expanded', String(open));
      menuToggle.querySelector('span').textContent = open ? 'Close' : 'Menu';
    });

    navLinks.addEventListener('click', function (event) {
      var link = event.target.closest('a');
      if (!link || !compactNav.matches) return;
      closeMenu(false);
      var href = link.getAttribute('href');
      var target = href.charAt(0) === '#' ? document.getElementById(href.slice(1)) : null;
      if (target) {
        target.focus({ preventScroll: true });
      } else {
        menuToggle.focus();
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && nav.classList.contains('menu-open')) {
        closeMenu(true);
      }
    });
    document.addEventListener('click', function (event) {
      if (!nav.contains(event.target)) closeMenu(false);
    });
    compactNav.addEventListener('change', function () {
      closeMenu(false);
    });
  }

  var contents = document.getElementById('article-contents');
  if (contents) {
    var wideScreen = window.matchMedia('(min-width: 769px)');
    contents.open = wideScreen.matches;
    wideScreen.addEventListener('change', function (event) {
      contents.open = event.matches;
    });
    contents.querySelector('nav').addEventListener('click', function (event) {
      var link = event.target.closest('a');
      if (!link) return;
      var target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
      if (target) {
        target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
      }
    });
  }

  var viewer = document.getElementById('image-viewer');
  if (viewer && typeof viewer.showModal === 'function') {
    var viewerImage = viewer.querySelector('img');
    var originalLink = viewer.querySelector('a');
    var imageTrigger = null;

    document.querySelectorAll('.article-body img').forEach(function (image, index) {
      if (image.closest('a, button')) return;
      var trigger = document.createElement('button');
      trigger.type = 'button';
      trigger.className = 'image-zoom';
      trigger.setAttribute('aria-label', 'View larger: ' + (image.alt || 'article diagram ' + (index + 1)));
      trigger.setAttribute('aria-haspopup', 'dialog');
      var hint = document.createElement('span');
      hint.className = 'image-zoom-hint';
      hint.textContent = 'View larger';
      image.parentNode.insertBefore(trigger, image);
      trigger.appendChild(image);
      trigger.appendChild(hint);
      trigger.addEventListener('click', function () {
        viewerImage.src = image.currentSrc || image.src;
        viewerImage.alt = image.alt || 'Full-size article diagram';
        originalLink.href = viewerImage.src;
        imageTrigger = trigger;
        viewer.showModal();
        viewer.querySelector('.image-viewer-scroll').scrollTo(0, 0);
        document.body.classList.add('image-viewer-open');
      });
    });

    viewer.querySelector('button').addEventListener('click', function () {
      viewer.close();
    });
    viewer.addEventListener('click', function (event) {
      if (event.target === viewer) viewer.close();
    });
    viewer.addEventListener('close', function () {
      document.body.classList.remove('image-viewer-open');
      viewerImage.removeAttribute('src');
      if (imageTrigger) imageTrigger.focus({ preventScroll: true });
    });
  }
})();
