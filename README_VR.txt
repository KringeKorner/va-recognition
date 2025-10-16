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
usable footage is available to prevent power drain and system usage.