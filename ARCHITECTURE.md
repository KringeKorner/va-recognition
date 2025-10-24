#Overview
Outlines the architecture development over time and notes any changes per development period.

#24/10/2025 - Cycle 1
Cycle 1 has initial notes on the software prototype. Details are very high level.

#General structure
Main Processor Unit
├─Input from VR Module
├─Input from AR Module
├─IO to VAI module
├─IO to AAI module
├─Output line
└─Input line

#VR Module
├─Main Controller
│ ├─IO to Recorder Module
│ ├─IO to MINERVA
│ └─IO to Analyzer unit
├─Recorder Unit
│ └─IO to Main Controller
├─Analyzer Unit
│ └─IO to Main Controller
├─MINERVA Overlay
│ └─Output from Main Controller
└─Output to Main Processor

#AR Module
├─Main Controller
│ ├─IO to Recorder Module
│ └─IO to S2T unit
├─Recorder Unit
│ └─IO to Main Controller
├─S2T Unit
│ └─IO to Main Controller
└─Output to Main Processor