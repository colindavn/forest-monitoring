const BOM = '﻿'

function cell(value: unknown): string {
  if (value == null) return ''
  const text = String(value)
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

/** RFC 4180 CSV (comma, CRLF, UTF-8 BOM so Excel keeps accents). */
export function toCsv<T extends object>(rows: T[], columns: (keyof T & string)[]): string {
  const lines = [columns.join(','), ...rows.map((r) => columns.map((c) => cell(r[c])).join(','))]
  return BOM + lines.map((l) => `${l}\r\n`).join('')
}

/** Trigger a browser download of `content` as a CSV file. */
export function downloadCsv(filename: string, content: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}
