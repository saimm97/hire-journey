import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { TextField } from './TextField'

describe('TextField validation state', () => {
  it('renders an accessible inline error for the addressed field', () => {
    render(
      <TextField
        label="From"
        value="May 2021"
        onChange={vi.fn()}
        fieldPath="education.0.start_date"
        error="Use YYYY or YYYY-MM."
      />,
    )

    const input = screen.getByRole('textbox', { name: 'From' })
    expect(input).toHaveAttribute('name', 'education.0.start_date')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAccessibleDescription('Use YYYY or YYYY-MM.')
    expect(screen.getByText('Use YYYY or YYYY-MM.')).toBeVisible()
  })
})
