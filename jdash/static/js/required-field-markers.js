(function () {
  function labelAlreadyMarked(label) {
    return Boolean(label.querySelector('.required-field-marker'))
      || Array.prototype.some.call(label.querySelectorAll('.text-danger'), function (element) {
        return element.textContent.indexOf('*') !== -1;
      });
  }

  function wrapPlainMarker(label) {
    var walker = document.createTreeWalker(label, NodeFilter.SHOW_TEXT);
    var textNode = walker.nextNode();

    while (textNode) {
      var markerIndex = textNode.nodeValue.indexOf('*');
      if (markerIndex !== -1) {
        var marker = document.createElement('span');
        marker.className = 'required-field-marker';
        marker.setAttribute('aria-hidden', 'true');
        marker.textContent = '*';

        var trailingText = textNode.splitText(markerIndex);
        trailingText.nodeValue = trailingText.nodeValue.substring(1);
        label.insertBefore(marker, trailingText);
        return true;
      }
      textNode = walker.nextNode();
    }

    return false;
  }

  function addMarker(label) {
    if (!label || labelAlreadyMarked(label)) {
      return;
    }

    if (wrapPlainMarker(label)) {
      return;
    }

    var marker = document.createElement('span');
    marker.className = 'required-field-marker';
    marker.setAttribute('aria-hidden', 'true');
    marker.textContent = '*';
    label.appendChild(marker);
  }

  function markRequiredFields(root) {
    var scope = root && root.querySelectorAll ? root : document;

    scope.querySelectorAll('.form-group.required label, .form-outline.required label').forEach(addMarker);

    scope.querySelectorAll('input[required], select[required], textarea[required]').forEach(function (field) {
      if (!field.id || field.type === 'hidden') {
        return;
      }

      var labels = document.querySelectorAll('label[for]');
      for (var index = 0; index < labels.length; index += 1) {
        if (labels[index].htmlFor === field.id) {
          addMarker(labels[index]);
          break;
        }
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    markRequiredFields(document);

    var observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        mutation.addedNodes.forEach(function (node) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            markRequiredFields(node);
          }
        });
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  });
})();
