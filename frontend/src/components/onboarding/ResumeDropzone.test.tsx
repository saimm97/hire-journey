import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ResumeDropzone } from './ResumeDropzone'

describe('ResumeDropzone', () => {
  it('opens the file chooser from Enter and Space', async () => {
    const user = userEvent.setup()
    const { container } = render(<ResumeDropzone onFile={vi.fn()} parsing={false} />)
    const dropzone = screen.getByRole('button', { name: /upload resume/i })
    const input = container.querySelector<HTMLInputElement>('input[type="file"]')!
    const click = vi.spyOn(input, 'click')

    dropzone.focus()
    await user.keyboard('{Enter}')
    await user.keyboard(' ')

    expect(click).toHaveBeenCalledTimes(2)
  })

  it('allows the same file to be selected again', async () => {
    const user = userEvent.setup()
    const onFile = vi.fn()
    const { container } = render(<ResumeDropzone onFile={onFile} parsing={false} />)
    const input = container.querySelector<HTMLInputElement>('input[type="file"]')!
    const file = new File(['%PDF'], 'resume.pdf', { type: 'application/pdf' })

    await user.upload(input, file)
    expect(input.value).toBe('')
    await user.upload(input, file)

    expect(onFile).toHaveBeenCalledTimes(2)
    expect(onFile).toHaveBeenNthCalledWith(1, file)
    expect(onFile).toHaveBeenNthCalledWith(2, file)
  })
})
