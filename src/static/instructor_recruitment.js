// Set UI for editing Instructor Recruitment notes.
const editInstructorRecruitmentNotes = (button) => {
  button.parentElement.classList.add("d-none");
  button.parentElement.parentElement
    .querySelector(".notes-editing")
    .classList.remove("d-none");
};

// Cancel UI for editing Instructor Recruitment notes.
const cancelSavingInstructorRecruitmentNotes = (button) => {
  const notesTextarea = button.parentElement.querySelector(".notes-content-editable");
  const notesValidationError = button.parentElement.querySelector(".invalid-feedback");
  const notesContent =
    button.parentElement.parentElement.querySelector(".notes-content");

  button.parentElement.classList.add("d-none");
  button.parentElement.parentElement.querySelector(".notes").classList.remove("d-none");

  notesTextarea.classList.remove("is-invalid");
  notesValidationError.classList.add("d-none");
  notesTextarea.value = notesContent.textContent;
};

// Send Instructor Recruitment notes via PATCH.
const saveInstructorRecruitmentNotes = async (button, noteId) => {
  const notesTextarea = button.parentElement.querySelector(".notes-content-editable");
  const notesValidationError = button.parentElement.querySelector(".invalid-feedback");
  const notesContent =
    button.parentElement.parentElement.querySelector(".notes-content");
  const notes = notesTextarea.value;
  const csrftoken = Cookies.get("csrftoken");

  const response = await fetch(`/api/v1/instructorrecruitment/${noteId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrftoken,
    },
    mode: "same-origin",
    body: JSON.stringify({ notes }),
  });

  if (!response.ok) {
    console.error(
      `Error when saving InstructoRecruitment(${noteId}):`,
      response.statusText
    );
    notesTextarea.classList.add("is-invalid");
    notesValidationError.classList.remove("d-none");
  } else {
    const data = await response.json();
    console.log("Success:", data);
    notesContent.textContent = data.notes;
    notesTextarea.classList.remove("is-invalid");
    notesValidationError.classList.add("d-none");

    button.parentElement.classList.add("d-none");
    button.parentElement.parentElement
      .querySelector(".notes")
      .classList.remove("d-none");
  }
};
