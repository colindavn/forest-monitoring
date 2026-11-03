// Chart colours (validated with the dataviz palette validator, light surface #fcfcfb).

export const INK = {
  primary: '#0b0b0b',
  secondary: '#52514e',
  muted: '#898781',
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  surface: '#fcfcfb',
}

/** Annual loss bars and their 5-year average line (categorical slots 1-2). */
export const LOSS_COLORS = { bars: '#2a78d6', avg: '#eb6834' }

/** Confidence is ordinal → one-hue ramp, lightest = nominal. */
export const CONFIDENCE_COLORS = { nominal: '#86b6ef', high: '#2a78d6', highest: '#104281' }

/** Anomaly is a state → status "critical", always paired with a ▲ marker and a label. */
export const ANOMALY_COLOR = '#d03b3b'
export const ROLLING_COLOR = INK.secondary

export const AXIS = {
  axisLine: { lineStyle: { color: INK.axis } },
  axisTick: { show: false },
  axisLabel: { color: INK.muted },
  splitLine: { lineStyle: { color: INK.grid } },
}
