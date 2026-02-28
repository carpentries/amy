window.addEventListener("load", () => {
  // find all DELETE checkboxes and set "click" handler
  document
    .querySelectorAll("input[type=checkbox][name$=DELETE]")
    .forEach((element) => {
      element.addEventListener("click", (clickEvent) => {
        // The element gets checked as soon as user clicks it, before
        // event.preventDefault is called. That's why we're looking for checked=true
        // element to confirm if user truly wants to remove it.
        if (element.checked) {
          const clickConfirmed = confirm(
            "Are you sure you want to delete this account owner?"
          );
          if (!clickConfirmed) clickEvent.preventDefault();
        }
      });
    });
});
