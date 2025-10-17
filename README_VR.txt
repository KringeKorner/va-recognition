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

The video capture is going to be sent to MINERVA and to the AI software that will
return the respective emotion of the individual. Analysis software is going to
accept the feed from the video recorder and draw bounding boxes around key
landmarks.

Landmarks have varying levels. A general landmark is considered to be a person.
A bounding landmark is the face of a person. A key landmark are features such as
the eyes and mouth. A flag is going to be sent with respect to these landmarks to
launch different processes. 

The varying flags are:
    1. NO_LANDMARK - no person detected for period of time
    2. GENERAL_LANDMARK - Person detected, but face is obscured or otherwise
                          undetectable
    3. KEY_DETECTED - Key landmark detected, send footage for analysis

The flags will essentially queue the heavy analysis software to trigger only when
usable footage is available to prevent power drain and system usage. Before the
status flag is set, there must be a certain amount of time or identical hits to
average out the state and ensure the flag is accurate.

MINERVA and the analysis model will receive the same frames, just at different
intervals. The analysis model receives frames only under the condition the
KEY_DETECTED flag is set, and MINERVA receives frames whenever the logging
interval is triggered. The analysis model currently is built to have a single
output, but will be expanded to also output a confidence percentage. All 
outputs are calculated similar to flag status, however once they are sent
outside of the analysis module, they will be considered as
accurate-without-fail and will not be checked nor averaged. The analysis
module will have 2 conditions that determine when it produces work. The
first condition is the KEY_DETECTED flag is set. While this condition is
met, the module will be configured to receive frames of data from the recorder
module. The internal condition is a while frames received loop. This makes
sure that there is actual data being received and is usable for analysis
purposes. By default, the output mood is set to NULL and the confidence
percentage is set to 0.00%. Whenever the loop is repeated, these values
are reset to their defaults and only when overwritten once an analysis is
performed that they are overwritten and sent out to be used.