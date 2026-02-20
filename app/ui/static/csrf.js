(function () {
  function readToken() {
    var el = document.querySelector('meta[name="csrf-token"]');
    return el ? el.getAttribute('content') || '' : '';
  }

  var token = readToken();
  if (!token) {
    return;
  }

  document.body.addEventListener('htmx:configRequest', function (event) {
    event.detail.headers['X-CSRF-Token'] = token;
  });

  var forms = document.querySelectorAll('form[method="post"], form[method="POST"]');
  forms.forEach(function (form) {
    try {
      var actionUrl = new URL(form.getAttribute('action') || window.location.href, window.location.origin);
      if (!actionUrl.searchParams.has('csrf_token')) {
        actionUrl.searchParams.set('csrf_token', token);
        form.setAttribute('action', actionUrl.pathname + actionUrl.search + actionUrl.hash);
      }
    } catch (e) {
      // Ignore malformed action URLs and rely on hidden input fallback.
    }

    if (form.querySelector('input[name="csrf_token"]')) {
      return;
    }
    var input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'csrf_token';
    input.value = token;
    form.appendChild(input);
  });
})();
