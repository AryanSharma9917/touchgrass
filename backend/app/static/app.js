const form = document.querySelector("#mission-form");
const message = document.querySelector("#form-message");
const result = document.querySelector("#mission-result");
const phoneFreeView = document.querySelector("#phone-free-view");
const submitButton = form.querySelector(".submit-button");

function splitList(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function fillList(list, items) {
  list.replaceChildren();
  for (const item of items) {
    const element = document.createElement("li");
    element.textContent = item;
    list.append(element);
  }
}

function fillMissionSteps(list, steps) {
  list.replaceChildren();
  for (const step of steps) {
    const element = document.createElement("li");
    const duration = document.createElement("strong");
    const instruction = document.createElement("span");
    duration.className = "step-duration";
    duration.textContent = `${step.duration_minutes} min`;
    instruction.textContent = step.instruction;
    element.append(duration, instruction);
    list.append(element);
  }
}

function showMission(mission) {
  document.querySelector("#mission-title").textContent = mission.title;
  document.querySelector("#mission-description").textContent =
    mission.short_description;
  document.querySelector("#mission-duration").textContent =
    `${mission.estimated_duration} minutes`;
  document.querySelector("#mission-completion").textContent =
    mission.completion_message;

  const preparationSection = document.querySelector("#preparation-section");
  preparationSection.hidden = mission.preparation.length === 0;
  fillList(document.querySelector("#mission-preparation"), mission.preparation);
  fillMissionSteps(document.querySelector("#mission-steps"), mission.steps);
  fillList(document.querySelector("#mission-safety"), mission.safety_notes);

  const challengeSection = document.querySelector("#challenge-section");
  challengeSection.hidden = !mission.optional_challenge;
  document.querySelector("#mission-challenge").textContent =
    mission.optional_challenge || "";

  document.querySelector("#phone-free-title").textContent = mission.title;
  document.querySelector("#phone-free-duration").textContent =
    `${mission.estimated_duration} minutes`;
  document.querySelector("#phone-free-preparation-section").hidden =
    mission.preparation.length === 0;
  fillList(
    document.querySelector("#phone-free-preparation"),
    mission.preparation,
  );
  fillMissionSteps(document.querySelector("#phone-free-steps"), mission.steps);
  form.hidden = true;
  result.hidden = false;
  message.textContent = "";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  const values = new FormData(form);
  const payload = {
    available_time_minutes: Number(values.get("available_time_minutes")),
    preferred_activity: values.get("preferred_activity"),
    energy_level: values.get("energy_level"),
    environment: values.get("environment"),
    interests: splitList(values.get("interests") || ""),
    constraints: splitList(values.get("constraints") || ""),
    phone_free: values.get("phone_free") === "on",
  };

  submitButton.disabled = true;
  submitButton.querySelector("span").textContent = "…";
  message.textContent = "Making a practical plan for your time outside…";
  result.hidden = true;

  try {
    const response = await fetch("/api/missions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let data;
    try {
      data = await response.json();
    } catch {
      throw new Error("The server returned an unreadable response. Try again.");
    }
    if (!response.ok) {
      throw new Error(data.detail?.message || "Could not create a mission. Try again.");
    }
    showMission(data);
  } catch (error) {
    message.textContent = error.message || "Could not reach the app. Try again.";
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector("span").textContent = "↗";
  }
});

document.querySelector("#phone-free-button").addEventListener("click", () => {
  result.hidden = true;
  phoneFreeView.hidden = false;
  document.body.classList.add("phone-free-active");
  window.scrollTo({ top: 0, behavior: "smooth" });
});

document.querySelector("#return-button").addEventListener("click", () => {
  phoneFreeView.hidden = true;
  result.hidden = false;
  document.body.classList.remove("phone-free-active");
});

document.querySelector("#edit-mission-button").addEventListener("click", () => {
  result.hidden = true;
  form.hidden = false;
  form.scrollIntoView({ behavior: "smooth", block: "start" });
});
