import { useMemo } from "react";
import { City, Country, State } from "country-state-city";
import type { ComboboxSuggestion } from "@/components/ui/field-menu";

/**
 * Country / state / city autocomplete over the `country-state-city` dataset.
 *
 * Extracted from AuditPanel so the Lead Magnet console's pre-flight modal asks
 * for a location the same way the tool page does. Two implementations reading
 * the same 150k-row dataset would drift in exactly the places that matter — the
 * order of suggestions, whether an unlisted place is still accepted, and which
 * field gates which — and the two forms feed the SAME backend field.
 *
 * SUGGESTIONS ONLY, NEVER A CONSTRAINT. Typed text is always kept: the dataset
 * does not know every place, and an unlisted one must still be auditable. That
 * is why these are comboboxes rather than dropdowns, and why `countryMatch` /
 * `stateMatch` are exposed as *optional* — a caller uses them to narrow the next
 * field, not to validate the previous one.
 */

/**
 * How many suggestions to show. Deliberately short: these lists are long enough
 * (150k+ cities) that a scrolling panel is slower to read than retyping.
 */
export const MAX_LOCATION_SUGGESTIONS = 6;

/** Cities are only searched from two characters — one letter matches thousands. */
const MIN_CITY_QUERY_LENGTH = 2;

function normalize(value: string) {
  return value.trim().toLowerCase();
}

export interface LocationQuery {
  country: string;
  state: string;
  /** Omit where the form has no city field; city suggestions are then unused. */
  city?: string;
}

export function useLocationSuggestions({ country, state, city = "" }: LocationQuery) {
  const countries = useMemo(() => Country.getAllCountries(), []);

  /** The typed country, only when it exactly names a real one. */
  const countryMatch = useMemo(
    () => countries.find((entry) => normalize(entry.name) === normalize(country)),
    [countries, country],
  );

  /** The typed state, only when it exactly names one inside `countryMatch`. */
  const stateMatch = useMemo(() => {
    if (!countryMatch) return undefined;
    return State.getStatesOfCountry(countryMatch.isoCode).find(
      (entry) => normalize(entry.name) === normalize(state),
    );
  }, [countryMatch, state]);

  const countrySuggestions = useMemo<ComboboxSuggestion[]>(() => {
    const query = normalize(country);
    if (!query) return [];
    return countries
      .filter((entry) => normalize(entry.name).startsWith(query))
      .slice(0, MAX_LOCATION_SUGGESTIONS)
      .map((entry) => ({ key: entry.isoCode, value: entry.name, label: entry.name }));
  }, [countries, country]);

  const stateSuggestions = useMemo<ComboboxSuggestion[]>(() => {
    const query = normalize(state);
    if (!query) return [];
    // Without a known country every state name on earth is a candidate, so the
    // country is required first rather than searching globally.
    if (!countryMatch) return [];
    return State.getStatesOfCountry(countryMatch.isoCode)
      .filter((entry) => normalize(entry.name).startsWith(query))
      .slice(0, MAX_LOCATION_SUGGESTIONS)
      .map((entry) => ({
        key: `${entry.countryCode}-${entry.isoCode}`,
        value: entry.name,
        label: entry.name,
      }));
  }, [countryMatch, state]);

  const citySuggestions = useMemo<ComboboxSuggestion[]>(() => {
    const query = normalize(city);
    if (query.length < MIN_CITY_QUERY_LENGTH) return [];

    const pool = stateMatch
      ? City.getCitiesOfState(stateMatch.countryCode, stateMatch.isoCode)
      : countryMatch
        ? (City.getCitiesOfCountry(countryMatch.isoCode) ?? [])
        : [];
    if (!pool.length) return [];

    return pool
      .filter((entry) => normalize(entry.name).startsWith(query))
      .slice(0, MAX_LOCATION_SUGGESTIONS)
      .map((entry, index) => {
        const stateName =
          State.getStateByCodeAndCountry(entry.stateCode, entry.countryCode)?.name ??
          entry.stateCode;
        return {
          // Duplicate city names within one state are common enough that the name
          // alone is not a stable key.
          key: `${entry.countryCode}-${entry.stateCode}-${entry.name}-${index}`,
          value: entry.name,
          // When the state is already known every candidate shares it, so naming
          // it again in each row is noise.
          label: stateMatch ? entry.name : `${entry.name}, ${stateName}`,
          // Carried so selecting a city can fill the state it belongs to.
          data: { state: stateName },
        };
      });
  }, [city, countryMatch, stateMatch]);

  return { countryMatch, stateMatch, countrySuggestions, stateSuggestions, citySuggestions };
}
