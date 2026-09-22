document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert-close').forEach((button) => {
    button.addEventListener('click', () => button.parentElement.remove());
  });
  document.querySelectorAll('input[type="date"]').forEach((input) => {
    input.max = new Date().toISOString().split('T')[0];
  });
});
