function showJdashLoading(message) {
  var overlay = document.getElementById('jdash-loading-overlay');
  var messageElement = document.getElementById('jdash-loading-message');

  if (!overlay) {
    return;
  }

  if (messageElement && message) {
    messageElement.textContent = message;
  }

  overlay.style.display = 'flex';
  overlay.hidden = false;
  overlay.setAttribute('aria-hidden', 'false');
  document.body.classList.add('jdash-loading-active');
}

function hideJdashLoading() {
  var overlay = document.getElementById('jdash-loading-overlay');

  if (!overlay) {
    return;
  }

  overlay.hidden = true;
  overlay.style.display = 'none';
  overlay.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('jdash-loading-active');
}

window.showJdashLoading = showJdashLoading;
window.hideJdashLoading = hideJdashLoading;

window.addEventListener('pageshow', function () {
  hideJdashLoading();
});
