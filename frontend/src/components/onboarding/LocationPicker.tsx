"use client"

import { useState } from "react"
import { City, Country, State } from "country-state-city"
import { Plus } from "lucide-react"

const SELECT =
  "w-full rounded-lg border border-brand-border bg-white px-3 py-2 text-sm text-brand-ink " +
  "outline-none transition-all focus:border-brand-violet focus:ring-2 focus:ring-brand-violet/20"

interface LocationPickerProps {
  /** Called with the composed label, e.g. "Berlin, Berlin, Germany" or "Germany". */
  onSelect: (label: string) => void
  buttonLabel?: string
}

/**
 * Cascading country -> state -> city selects backed by country-state-city.
 * Deliberately default-exported and imported via next/dynamic: the bundled
 * dataset is large, so it must stay out of the route's main chunk.
 */
export default function LocationPicker({ onSelect, buttonLabel = "Add" }: LocationPickerProps) {
  const [countryCode, setCountryCode] = useState("")
  const [stateCode, setStateCode] = useState("")
  const [cityName, setCityName] = useState("")

  const countries = Country.getAllCountries()
  const states = countryCode ? State.getStatesOfCountry(countryCode) : []
  const cities = countryCode && stateCode ? City.getCitiesOfState(countryCode, stateCode) : []

  const country = countries.find((c) => c.isoCode === countryCode)
  const state = states.find((s) => s.isoCode === stateCode)

  const commit = () => {
    if (!country) return
    const label = [cityName, state?.name, country.name].filter(Boolean).join(", ")
    onSelect(label)
    setCityName("") // keep country/state for quickly adding nearby places
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        value={countryCode}
        onChange={(event) => {
          setCountryCode(event.target.value)
          setStateCode("")
          setCityName("")
        }}
        aria-label="Country"
        className={`${SELECT} max-w-56`}
      >
        <option value="">Country…</option>
        {countries.map((c) => (
          <option key={c.isoCode} value={c.isoCode}>
            {c.name}
          </option>
        ))}
      </select>

      {states.length > 0 && (
        <select
          value={stateCode}
          onChange={(event) => {
            setStateCode(event.target.value)
            setCityName("")
          }}
          aria-label="State or region"
          className={`${SELECT} max-w-56`}
        >
          <option value="">State / region…</option>
          {states.map((s) => (
            <option key={s.isoCode} value={s.isoCode}>
              {s.name}
            </option>
          ))}
        </select>
      )}

      {cities.length > 0 && (
        <select
          value={cityName}
          onChange={(event) => setCityName(event.target.value)}
          aria-label="City"
          className={`${SELECT} max-w-56`}
        >
          <option value="">City…</option>
          {cities.map((c) => (
            <option key={`${c.name}-${c.latitude}`} value={c.name}>
              {c.name}
            </option>
          ))}
        </select>
      )}

      <button
        type="button"
        onClick={commit}
        disabled={!country}
        className="inline-flex items-center gap-1 rounded-full border border-brand-border bg-white px-3 py-1.5 text-sm text-brand-muted transition-colors hover:border-brand-violet/60 hover:text-brand-ink disabled:opacity-50"
      >
        <Plus className="size-4" /> {buttonLabel}
      </button>
    </div>
  )
}
