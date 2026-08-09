/* Confirmation modal for the "Accept & match" action on the training requests list.

   Trainees state in their training request which offering (benefit) they signed up for.
   The admin may match them to a different one, either by picking an "Allocated account
   benefit" or, when auto-matching, a "Benefit for auto-match". When any of the selected
   trainees asked for something else, we ask the admin to confirm first.

   The `Benefit` behind an option is read from `data-benefit-id` / `data-benefit-name` for
   options rendered by Django, and from `benefit_id` / `benefit_name` returned by the
   lookup views for options fetched over AJAX by Select2. */

/* Return {id, name} of the benefit behind currently selected option, or null. */
function selectedBenefit(select) {
  if (!select || !select.value) return null;

  const option = select.selectedOptions[0];
  // Select2 keeps the lookup response for options it created itself.
  const data = ($(select).data("select2") && $(select).select2("data")[0]) || {};

  const id = data.benefit_id || (option && option.dataset.benefitId);
  if (!id) return null;

  return {
    id: id,
    name: data.benefit_name || (option && option.dataset.benefitName) || "",
  };
}

document.addEventListener("alpine:init", () => {
  Alpine.data("matchConfirmation", () => ({
    // Seeded from the "auto_assign" checkbox by `x-model.fill`; drives whether the
    // "Benefit for auto-match" field is enabled (see BulkMatchTrainingRequestForm).
    autoAssign: null,
    open: false,
    // Set once the admin confirms, so that the re-submit isn't intercepted again.
    confirmed: false,
    submitter: null,
    benefitName: "",
    mismatched: [],

    /* Benefit that the selected trainees would be matched to, or null if the chosen
       matching method doesn't use benefits (membership seats, or no seats at all). */
    targetBenefit() {
      const allocatedBenefit = this.$refs.form.querySelector("#id_allocated_benefit");
      const autoAssign = this.$refs.form.querySelector("#id_auto_assign");
      const benefitOverride = this.$refs.form.querySelector("#id_benefit_override");

      if (allocatedBenefit && allocatedBenefit.value) return selectedBenefit(allocatedBenefit);
      if (autoAssign && autoAssign.checked) return selectedBenefit(benefitOverride);
      return null;
    },

    /* Selected requests asking for a benefit other than `benefit`. Requests which don't
       specify a benefit are left out - there's nothing to disagree with. */
    mismatchedRequests(benefit) {
      const checkboxes = this.$refs.form.querySelectorAll('input[name="requests"]:checked');
      return Array.from(checkboxes)
        .filter((checkbox) => checkbox.dataset.benefitId && checkbox.dataset.benefitId !== benefit.id)
        .map((checkbox) => ({
          id: checkbox.value,
          trainee: checkbox.dataset.trainee,
          benefitName: checkbox.dataset.benefitName,
        }));
    },

    onSubmit(event) {
      if (this.confirmed) return;
      // Other buttons in this form (accept, discard, unmatch) don't assign benefits.
      if (!event.submitter || event.submitter.name !== "match") return;

      const benefit = this.targetBenefit();
      if (!benefit) return;

      const mismatched = this.mismatchedRequests(benefit);
      if (!mismatched.length) return;

      event.preventDefault();
      this.benefitName = benefit.name;
      this.mismatched = mismatched;
      this.submitter = event.submitter;
      this.setOpen(true);
    },

    proceed() {
      this.setOpen(false);
      this.confirmed = true;
      this.$refs.form.requestSubmit(this.submitter);
    },

    cancel() {
      this.setOpen(false);
      this.submitter = null;
    },

    /* `modal-open` stops the page underneath the backdrop from scrolling; normally
       Bootstrap's own modal JS takes care of it, but this modal is driven by Alpine. */
    setOpen(open) {
      this.open = open;
      document.body.classList.toggle("modal-open", open);
    },
  }));
});
