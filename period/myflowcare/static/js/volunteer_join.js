// static/js/volunteer_join.js
document.addEventListener('DOMContentLoaded', function () {
  var container = document.querySelector('[data-accepted]');
  if (!container) return;

  var accepted = container.dataset.accepted === 'true';
  var display = container.dataset.displayName || 'the group';

  if (!accepted) return;

  try {
    var modalEl = document.getElementById('joinModal');
    if (window.bootstrap && modalEl) {
      var modal = new bootstrap.Modal(modalEl);
      modal.show();
    } else {
      alert('Thanks — you have joined ' + display + '.');
    }
  } catch (e) {
    console.warn('Error showing join modal:', e);
    alert('Thanks — you have joined ' + display + '.');
  }
});
