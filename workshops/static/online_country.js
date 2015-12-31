var prev_venue,
    prev_address,
    prev_latitude,
    prev_longitude,
    online_selected_before = false;

var id_country = '#id_country, #id_event-country',
    id_venue = '#id_venue, #id_event-venue',
    id_address = '#id_address, #id_event-address',
    id_latitude = '#id_latitude, #id_event-latitude',
    id_longitude = '#id_longitude, #id_event-longitude';

if ($(id_country).val() == 'W3') {
    online_selected_before = true;
    $(id_venue).prop('disabled', true);
    $(id_address).prop('disabled', true);
    $(id_latitude).prop('disabled', true);
    $(id_longitude).prop('disabled', true);
}

// disable latitude, longitude inputs if online country selected
$(id_country).change(function(e) {
  var new_country = $(e.target).val();

  if (new_country == 'W3') {
    prev_venue = $(id_venue).val();
    prev_address = $(id_address).val();
    prev_latitude = $(id_latitude).val();
    prev_longitude = $(id_longitude).val();
    $(id_venue).val('Internet');
    $(id_address).val('Internet');
    $(id_latitude).val('-48.876667');
    $(id_longitude).val('-123.393333');
    $(id_venue).prop('disabled', true);
    $(id_address).prop('disabled', true);
    $(id_latitude).prop('disabled', true);
    $(id_longitude).prop('disabled', true);
    online_selected_before = true;
  } else if (online_selected_before) {
    $(id_venue).val(prev_venue);
    $(id_address).val(prev_address);
    $(id_latitude).val(prev_latitude);
    $(id_longitude).val(prev_longitude);
    $(id_venue).prop('disabled', false);
    $(id_address).prop('disabled', false);
    $(id_latitude).prop('disabled', false);
    $(id_longitude).prop('disabled', false);
    online_selected_before = false;
  }
});
