import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { YearMonthField } from './YearMonthField'

function Harness({ initial = '' }: { initial?: string }) {
  const [value, setValue] = useState(initial)
  return (
    <YearMonthField
      label="From"
      value={value}
      onChange={setValue}
      fieldPath="education.0.start_date"
    />
  )
}

describe('YearMonthField', () => {
  it('uses the native month picker by default and can switch to year-only', async () => {
    const user = userEvent.setup()
    render(<Harness />)

    expect(screen.getByLabelText('From')).toHaveAttribute('type', 'month')
    await user.click(screen.getByRole('button', { name: 'Use year only for From' }))

    const yearInput = screen.getByRole('textbox', { name: 'From' })
    expect(yearInput).toHaveAttribute('inputmode', 'numeric')
    expect(yearInput).toHaveAttribute('pattern', '\\d{4}')
    await user.type(yearInput, '2026')
    expect(yearInput).toHaveValue('2026')
  })

  it('shows an extracted year and only drops it when month precision is requested', async () => {
    const user = userEvent.setup()
    render(<Harness initial="2021" />)

    expect(screen.getByRole('textbox', { name: 'From' })).toHaveValue('2021')
    await user.click(screen.getByRole('button', { name: 'Use month picker for From' }))

    const monthInput = screen.getByLabelText('From')
    expect(monthInput).toHaveAttribute('type', 'month')
    expect(monthInput).toHaveValue('')
  })

  it('reduces a selected month to its year when year-only is requested', async () => {
    const user = userEvent.setup()
    render(<Harness initial="2021-09" />)

    await user.click(screen.getByRole('button', { name: 'Use year only for From' }))

    expect(screen.getByRole('textbox', { name: 'From' })).toHaveValue('2021')
  })
})
