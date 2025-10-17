// static/js/book_appointment.js
document.addEventListener('DOMContentLoaded', function () {
  var container = document.querySelector('[data-accepted]');
  if (!container) return;

  var accepted = container.dataset.accepted === 'true';
  var doctorName = container.dataset.doctorName || 'The doctor';

  if (!accepted) return;

  try {
    var modalEl = document.getElementById('acceptModal');
    if (window.bootstrap && modalEl) {
      var modal = new bootstrap.Modal(modalEl);
      modal.show();
    } else {
      alert(doctorName + ' has accepted your appointment.');
    }
  } catch (e) {
    console.warn('Error showing appointment accepted modal:', e);
    alert(doctorName + ' has accepted your appointment.');
  }
});
