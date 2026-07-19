import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import LocationPicker from "./LocationPicker"

describe("LocationPicker", () => {
  it("adds a country-only location", async () => {
    const onSelect = vi.fn()
    render(<LocationPicker onSelect={onSelect} buttonLabel="Add location" />)

    await userEvent.selectOptions(screen.getByLabelText("Country"), "DE")
    await userEvent.click(screen.getByRole("button", { name: /Add location/ }))

    expect(onSelect).toHaveBeenCalledWith("Germany")
  })

  it("composes city, state, and country into one label", async () => {
    const onSelect = vi.fn()
    render(<LocationPicker onSelect={onSelect} />)

    await userEvent.selectOptions(screen.getByLabelText("Country"), "DE")
    await userEvent.selectOptions(screen.getByLabelText("State or region"), "BE")
    await userEvent.selectOptions(screen.getByLabelText("City"), "Berlin")
    await userEvent.click(screen.getByRole("button", { name: /Add/ }))

    expect(onSelect).toHaveBeenCalledWith("Berlin, Berlin, Germany")
  })

  it("blocks adding until a country is picked", () => {
    render(<LocationPicker onSelect={() => {}} />)
    expect(screen.getByRole("button", { name: /Add/ })).toBeDisabled()
  })
})
