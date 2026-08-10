import { describe, expect, it } from 'vitest'

import { ApiError } from './client'
import { apiFieldErrors, groupError, pathKey } from './fieldErrors'

const errorWith = (fields: Array<{ path: Array<string | number>; message: string }>) =>
  new ApiError(422, { message: 'Some details need fixing.', code: 'validation_error', fields })

describe('apiFieldErrors', () => {
  it('flattens paths into dotted keys', () => {
    const errors = apiFieldErrors(
      errorWith([{ path: ['education', 0, 'start_date'], message: 'Bad date.' }]),
    )

    expect(errors).toEqual({ 'education.0.start_date': 'Bad date.' })
  })

  it('strips only the requested section', () => {
    const error = errorWith([
      { path: ['details', 'first_name'], message: 'Required.' },
      { path: ['preferences', 'desired_roles'], message: 'Pick one.' },
    ])

    expect(apiFieldErrors(error, { section: 'details' })).toEqual({
      first_name: 'Required.',
      'preferences.desired_roles': 'Pick one.',
    })
  })

  it('keeps the first message for a repeated path', () => {
    // First-wins, because the caller focuses the first key it finds.
    const errors = apiFieldErrors(
      errorWith([
        { path: ['title'], message: 'First.' },
        { path: ['title'], message: 'Second.' },
      ]),
    )

    expect(errors.title).toBe('First.')
  })

  it('preserves field order, which decides what gets focused', () => {
    const errors = apiFieldErrors(
      errorWith([
        { path: ['last_name'], message: 'B.' },
        { path: ['first_name'], message: 'A.' },
      ]),
    )

    expect(Object.keys(errors)).toEqual(['last_name', 'first_name'])
  })

  it('drops an entry whose path is only the section', () => {
    // A whole-request error has no control to address.
    const error = errorWith([{ path: ['details'], message: 'Provide a section.' }])

    expect(apiFieldErrors(error, { section: 'details' })).toEqual({})
  })

  it('applies remapPath after stripping the section', () => {
    const error = errorWith([{ path: ['details', 'projects', 0], message: 'Stale.' }])

    const errors = apiFieldErrors(error, {
      section: 'details',
      remapPath: (path) => (path[0] === 'projects' ? ['projects', 7, ...path.slice(2)] : path),
    })

    expect(errors).toEqual({ 'projects.7': 'Stale.' })
  })

  it('never mutates the paths on the error it was given', () => {
    const error = errorWith([{ path: ['details', 'projects', 0], message: 'Stale.' }])

    apiFieldErrors(error, {
      section: 'details',
      remapPath: (path) => [path[0]!, 9, ...path.slice(2)],
    })

    expect(error.fields[0]!.path).toEqual(['details', 'projects', 0])
  })
})

describe('groupError', () => {
  it('prefers an exact match, then the first nested one', () => {
    const errors = { work_modes_preferred: 'Pick one.', 'desired_roles.0': 'Too long.' }

    expect(groupError(errors, 'work_modes_preferred')).toBe('Pick one.')
    // A toggle group cannot address `desired_roles.0`, so it looks up the group.
    expect(groupError(errors, 'desired_roles')).toBe('Too long.')
    expect(groupError(errors, 'seniority_level')).toBeUndefined()
  })
})

describe('pathKey', () => {
  it('joins mixed segments with dots', () => {
    expect(pathKey(['projects', 1, 'name'])).toBe('projects.1.name')
  })
})
