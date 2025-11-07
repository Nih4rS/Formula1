import createPlotlyComponent from 'react-plotly.js/factory'
// @ts-expect-error no types for dist-min
import Plotly from 'plotly.js-dist-min'

const Plot = createPlotlyComponent(Plotly)
export default Plot

