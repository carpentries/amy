// disable latitude, longitude inputs if online country selected
$(function () {
  const id_country = "#id_country, #id_event-country";
  const id_venue = "#id_venue, #id_event-venue";
  const id_address = "#id_address, #id_event-address";
  const id_latitude = "#id_latitude, #id_event-latitude";
  const id_longitude = "#id_longitude, #id_event-longitude";
  const online_country = "W3";

  if ($(id_country).val() == online_country) {
    $(id_venue).prop("disabled", true);
    $(id_address).prop("disabled", true);
    $(id_latitude).prop("disabled", true);
    $(id_longitude).prop("disabled", true);
  }

  $(id_country).change(function (e) {
    var new_country = $(e.target).val();

    if (new_country == online_country) {
      $(id_venue).val("Internet");
      $(id_address).val("Internet");
      $(id_latitude).val("");
      $(id_longitude).val("");
      $(id_venue).prop("disabled", true);
      $(id_address).prop("disabled", true);
      $(id_latitude).prop("disabled", true);
      $(id_longitude).prop("disabled", true);
    } else {
      $(id_venue).prop("disabled", false);
      $(id_address).prop("disabled", false);
      $(id_latitude).prop("disabled", false);
      $(id_longitude).prop("disabled", false);
    }
  });
});
