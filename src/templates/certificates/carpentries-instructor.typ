// Instructor certificate. Values are passed in via `sys.inputs`, so they're always
// treated as plain text, never as Typst markup.
// Coordinates come from the original SVG (viewBox 0 0 792 612), including its `translate(-47,-11)`
// group transform, and denote text baselines.

#set page(width: 792pt, height: 612pt, margin: 0pt, background: image("carpentries-instructor-background.svg", width: 100%, height: 100%))
#set text(font: ("Liberation Sans", "Arial"), size: 14pt, fill: rgb("#808285"), top-edge: "baseline")

#let textline(y, body) = place(top + left, dx: 90.1107pt, dy: y * 1pt, body)

#textline(315.2737, [This certificate has been awarded for successfully completing The Carpentries Instructor Training])
#textline(340.8737, [program. The recipient has demonstrated understanding of core evidence-based teaching practices])
#textline(366.4737, [and pedagogical concepts, and is qualified to teach the core curriculum of Data Carpentry, Library])
#textline(392.0737, sys.inputs.carpentries)
#textline(433.2737, [Recipient: #sys.inputs.name])
#textline(458.8737, [Date of Award: #sys.inputs.date])
#textline(484.4737, [Certified by: #sys.inputs.signature])
