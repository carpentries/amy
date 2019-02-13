/* Checkbox saving functionality: saves checked checkboxes in sessionStorage
   (it's valid until user closes the tab) */

// encode Array with JSON to convert it to Storage object
function ArrayToStorage(data) {
  return JSON.stringify(data);
}

// decode Storage string result with JSON back into Array object
function StorageToArray(data) {
  return JSON.parse(data);
}

/* See http://learn.jquery.com/plugins/basic-plugin-creation/ */
$.fn.selectCheckboxesFromStorage = function (storageName) {
  // list of nearest checkboxes
  var checkboxes = $(this).closest('form')
                          .find(':checkbox[respond-to-select-all-checkbox]');

  if (sessionStorage.getItem(storageName)) {
    // read saved IDs, find corresponding checkboxes and check them
    var data = StorageToArray(sessionStorage.getItem(storageName));

    data.forEach(function(item) {
      checkboxes.closest('[value="' + item + '"]').prop('checked', true);
    });

  } else {
    // save default array value
    sessionStorage.setItem(storageName, ArrayToStorage(Array()));
  }

  return this;
}

$(document).ready(function() {
  // storage enabled
  if (typeof(Storage) !== "undefined") {
    // figure out storage name
    var storageName = 'TrainingRequests';

    // read checkboxes from storage and toggle them
    $('#table-requests').selectCheckboxesFromStorage(storageName);
    // update "select all" checkbox - just to be sure
    $('#table-requests :checkbox[select-all-checkbox]').updateSelectAllCheckbox();
    // update links for "*(Action)* selected"
    $('a[amy-download-selected]').each(function(i, obj) {
      $(this).updateIdsInHref();
    });


    // for each checkbox: save to / remove from Session upon a click
    $('#table-requests [respond-to-select-all-checkbox]').change(function() {
      var list = Array();
      var value = $(this).val();

      if (sessionStorage.getItem(storageName)) {
        list = StorageToArray(sessionStorage.getItem(storageName));
      } else {
        sessionStorage.setItem(storageName, ArrayToStorage(list));
      }

      if ($(this).prop('checked')) {
        // check if ID not in the list
        if (list.indexOf(value) == -1) {
          // if not in the list, add
          list.push(value);
        }
      } else {
        // check if ID in the list
        if (list.indexOf(value) != -1) {
          // if in the list, remove it
          list.splice(list.indexOf(value), 1);
        }
      }

      // save back to sessionStorage
      sessionStorage.setItem(storageName, ArrayToStorage(list));
    });


    // update whole session upon clicking "select-all-checkbox"
    $('#table-requests :checkbox[select-all-checkbox]').change(function() {
      var checkboxes = $(this).closest('form').find(':checkbox[respond-to-select-all-checkbox] :checked');
      var list = Array();

      // clear session storage entry
      sessionStorage.setItem(storageName, ArrayToStorage(list));

      // add to session storage
      checkboxes.each(function(i, obj) {
        var value = $(obj).val();
        if (list.indexOf(value) == -1) {
          // if not in the list, add
          list.push(value);
        }
      });

      // save back to sessionStorage
      sessionStorage.setItem(storageName, ArrayToStorage(list));
    });
  }
})

