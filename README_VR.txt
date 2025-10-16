The VR software is to be split into modules that are called by a main loop.
Goal is to allow modules to perform work in parallel and allow output to be a relatively
small load per module, rather than a single large script that executes larege amount
of work and potentially overload the processor.

MINERVA overlay is a diagnostic tool that will provide video capture and analysis
output as short bursts of captured video, time per capture and period tbd.

Main functionality is a combination of parallel processes of:
    1. Video capture.
    2. Video analysis.
    3. Diagnostic and poc tools.