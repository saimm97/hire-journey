import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ChipInput } from './ChipInput'

describe('ChipInput', () => {
  it('adds the draft on Enter and clears the input', async () => {
    const onAdd = vi.fn()
    render(<ChipInput values={[]} onAdd={onAdd} onRemove={() => {}} addLabel="Add tech" />)

    const input = screen.getByLabelText('Add tech')
    await userEvent.type(input, 'Python{Enter}')

    expect(onAdd).toHaveBeenCalledWith('Python')
    expect(input).toHaveValue('')
  })

  it('renders chips and removes one on click', async () => {
    const onRemove = vi.fn()
    render(
      <ChipInput values={['Python', 'FastAPI']} onAdd={() => {}} onRemove={onRemove} />,
    )

    expect(screen.getByText('Python')).toBeInTheDocument()
    await userEvent.click(screen.getByLabelText('Remove FastAPI'))
    expect(onRemove).toHaveBeenCalledWith('FastAPI')
  })
})
