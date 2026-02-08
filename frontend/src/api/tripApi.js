const API_BASE = "";

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export async function extractPreferences(userInput) {
  const res = await fetch(`${API_BASE}/api/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_input: userInput }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Extraction failed");
  }
  return res.json();
}

export async function refinePreferences(preferences, additionalInput, lastQuestion = null) {
  const body = { preferences, additional_input: additionalInput };
  if (lastQuestion) body.last_question = lastQuestion;
  const res = await fetch(`${API_BASE}/api/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Refinement failed");
  }
  return res.json();
}

export async function fetchWeather(city, country, startDate, endDate) {
  const params = new URLSearchParams({ city, country, start_date: startDate, end_date: endDate });
  const res = await fetch(`${API_BASE}/api/weather?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Weather fetch failed");
  }
  return res.json();
}

export async function generateItinerary(preferences) {
  const res = await fetch(`${API_BASE}/api/generate-itinerary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preferences }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Itinerary generation failed");
  }
  return res.json();
}
