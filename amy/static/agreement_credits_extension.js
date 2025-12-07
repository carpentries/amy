window.addEventListener("load", (e) => {
    const credits_input = document.querySelector("#id_credits");
    const diff_credits_input = document.querySelector("#id_diff_credits");
    const new_credits_input = document.querySelector("#id_new_credits");

    if (!!new_credits_input) {
        $(new_credits_input).on("change", (event) => {
            diff_credits_input.value = event.target.value - credits_input.value;
        });
    }
});
