import { createContext, useContext, useState, useCallback, useEffect } from "react";
import {
  checkHealth,
  extractPreferences,
  refinePreferences,
  generateItinerary as apiGenerateItinerary,
} from "../api/tripApi";

const TripContext = createContext(null);

/**
 * Compute the current conversation phase based on extracted preferences.
 * Mirrors the backend _get_next_question_phase logic.
 */
function getNextQuestionPhase(prefs) {
  if (!prefs) return null;
  if (!prefs.city) return "city";
  if (!prefs.country) return "country";
  if (!prefs.start_date && !prefs.end_date && !prefs.duration_days) return "dates";
  if (!prefs.pace) return "pace";
  if (prefs.needs_flight === null || prefs.needs_flight === undefined) return "flight";
  if (prefs.needs_flight && !prefs.source_location) return "source_location";
  if (prefs.needs_airbnb === null || prefs.needs_airbnb === undefined) return "airbnb";
  return null;
}

export function TripProvider({ children }) {
  const [phase, setPhase] = useState("welcome");
  const [messages, setMessages] = useState([]);
  const [preferences, setPreferences] = useState(null);
  const [validation, setValidation] = useState(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [itinerary, setItinerary] = useState(null);
  const [weather, setWeather] = useState(null);
  const [booking, setBooking] = useState(null);
  const [backendConnected, setBackendConnected] = useState(null);

  useEffect(() => {
    checkHealth()
      .then((data) => {
        setBackendConnected(data.nlp_service_ready);
      })
      .catch(() => {
        setBackendConnected(false);
      });
  }, []);

  const addMessage = useCallback((role, content) => {
    const msg = { id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, role, content, timestamp: Date.now() };
    setMessages((prev) => [...prev, msg]);
    return msg.id;
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim()) return;

      if (phase === "welcome") {
        setPhase("chat");
      }

      addMessage("user", text);
      setIsExtracting(true);

      try {
        let data;
        if (preferences) {
          // Compute the last question asked so backend can interpret yes/no correctly
          const lastQuestion = getNextQuestionPhase(preferences);
          data = await refinePreferences(preferences, text, lastQuestion);
        } else {
          data = await extractPreferences(text);
        }

        if (data.success) {
          setPreferences(data.preferences);
          setValidation(data.validation);

          const botMsg =
            data.bot_message || "I've updated your preferences. Check the panel on the right.";
          addMessage("bot", botMsg);

          if (data.saved_to_file) {
            addMessage("system", `Trip preferences saved to: ${data.saved_to_file}`);
          }
        } else {
          addMessage("bot", data.error || "Something went wrong. Please try again.");
        }
      } catch (err) {
        addMessage("bot", `Failed to process: ${err.message}`);
      } finally {
        setIsExtracting(false);
      }
    },
    [phase, preferences, addMessage]
  );

  const doGenerateItinerary = useCallback(async () => {
    if (!preferences) {
      addMessage("bot", "Please complete your trip preferences first.");
      return;
    }

    setIsGenerating(true);
    try {
      // Call the real backend — passes preferences, gets back itinerary + weather + booking
      const data = await apiGenerateItinerary(preferences);

      if (data.success) {
        setItinerary(data.itinerary);
        setPhase("itinerary");

        // Set weather indexed by date
        if (data.weather && data.weather.forecasts && data.weather.forecasts.length > 0) {
          const byDate = {};
          for (const f of data.weather.forecasts) {
            byDate[f.date] = f;
          }
          setWeather(byDate);
        } else {
          // Fallback: extract weather embedded in itinerary days (if any)
          const days = data.itinerary?.days || [];
          const fallback = {};
          for (const d of days) {
            if (d.weather) fallback[d.date] = d.weather;
          }
          if (Object.keys(fallback).length > 0) setWeather(fallback);
        }

        // Store booking links
        if (data.booking && !data.booking.skipped) {
          setBooking(data.booking);
        }
      } else {
        addMessage("bot", data.error || "Failed to generate itinerary. Please try again.");
      }
    } catch (err) {
      addMessage("bot", `Failed to generate itinerary: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  }, [addMessage, preferences]);

  const resetToChat = useCallback(() => {
    setPhase("chat");
  }, []);

  const resetAll = useCallback(() => {
    setPhase("welcome");
    setMessages([]);
    setPreferences(null);
    setValidation(null);
    setItinerary(null);
    setWeather(null);
    setBooking(null);
    setIsExtracting(false);
    setIsGenerating(false);
  }, []);

  return (
    <TripContext.Provider
      value={{
        phase,
        messages,
        preferences,
        validation,
        isExtracting,
        isGenerating,
        itinerary,
        weather,
        booking,
        backendConnected,
        sendMessage,
        generateItinerary: doGenerateItinerary,
        resetToChat,
        resetAll,
      }}
    >
      {children}
    </TripContext.Provider>
  );
}

export function useTrip() {
  const ctx = useContext(TripContext);
  if (!ctx) throw new Error("useTrip must be used within TripProvider");
  return ctx;
}
