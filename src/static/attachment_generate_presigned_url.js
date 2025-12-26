function getCookie(name) {
  const cookies = document.cookie.split("; ");
  for (let cookie of cookies) {
      const [key, value] = cookie.split("=");
      if (key === name) {
          return decodeURIComponent(value);
      }
  }
  return null; // Return null if not found
}

function generatePresignedUrl(pk) {
  const url = `/api/v2/attachment/${pk}/generate_presigned_url`;

  const csrfToken = getCookie("csrftoken") || "";

  fetch(url, {
      method: "POST",
      headers: {
          "Content-Type": "application/json",
          "X-CSRFTOKEN": csrfToken,
      },
      body: JSON.stringify({})
  })
  .then(_ => location.reload())
  .catch(error => console.error("Error:", error));
}
