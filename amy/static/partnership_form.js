jQuery(function () {
  $("#id_partner_organisation").on("change.select2", (e) => {
    const data = $(e.target).select2("data");
    const empty_data = (data.length == 0) || data[0].text === "";

    const id_partner_consortium = $("#id_partner_consortium");
    const id_name = $("#id_name");

    id_partner_consortium.prop("disabled", !empty_data);
    if (!empty_data)
    {
      const domain_indicator_position = data[0].text.lastIndexOf("<");
      const name_without_domain = data[0].text.slice(0, domain_indicator_position - 1);
      id_name.val(name_without_domain);
    }

    e.preventDefault();
  });

  $("#id_partner_consortium").on("change.select2", (e) => {
    const data = $(e.target).select2("data");
    const empty_data = (data.length == 0) || data[0].text === "";

    const id_partner_organisation = $("#id_partner_organisation");
    id_partner_organisation.prop("disabled", !empty_data);

    e.preventDefault();
  });
});
