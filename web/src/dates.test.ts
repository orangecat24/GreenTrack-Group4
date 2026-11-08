import { describe, expect, it } from 'vitest'
import { toWindow } from './dates'

describe('calendar date to API window', () => {
  it('makes the displayed final day inclusive using an exclusive UTC end', () => {
    expect(toWindow({ from: '2009-06-01', through: '2009-06-07' })).toEqual({ household_id: 'household-1', start: '2009-06-01T00:00:00.000Z', end: '2009-06-08T00:00:00.000Z' })
    expect(toWindow({ from: '2009-06-30', through: '2009-06-30' })?.end).toBe('2009-07-01T00:00:00.000Z')
  })
  it.each([
    { from: '', through: '2009-06-01' },
    { from: '2009-06-05', through: '2009-06-01' },
    { from: '2009-02-31', through: '2009-06-01' },
  ])('rejects invalid dates: %j', (selection) => { expect(toWindow(selection)).toBeNull() })
})
