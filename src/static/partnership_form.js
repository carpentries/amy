jQuery(function () {
  const creditsField = $("#id_credits");

  function updateCreditsField(tier) {
    if (tier !== undefined && tier.is_custom) {
      creditsField.prop("disabled", false);
    } else {
      creditsField.prop("disabled", true).val(tier.credits);
    }
  }

  // On page load, fetch the selected tier's data from the API to initialise the credits field.
  const initialTierId = $("#id_tier").val();
  if (initialTierId) {
    fetch(`/api/v2/partnershiptier/${initialTierId}`, { credentials: "same-origin" })
      .then((res) => res.json())
      .then((tier) => updateCreditsField(tier));
  } else {
    creditsField.prop("disabled", true);
  }

  // The lookup view returns is_custom and credits alongside id and text,
  // so they are available on e.params.data after the user selects a tier.
  $("#id_tier").on("change.select2", (e) => {
    const data = $(e.target).select2("data");
    updateCreditsField(data[0]);
    e.preventDefault();
  });

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
