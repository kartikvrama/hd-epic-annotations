PASSIVE_KETTLE_LONG = {
    "video_id": "P01-20240202-171220",
    "prompt": """Determine if the object 'kettle' is being used during the time period between 03:38 (218.07s) and 04:08 (248.07s).

Analyze the event history before providing your final answer using step-by-step Chain of Thought reasoning.

Event History:
Time: 03:38 (218.07s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put down the kettle back on its base.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [kettle]
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, second cover]
  counter.003: [glass, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [flask, glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: [cover of flask]
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: put down `kettle` to `counter.003`

Time: 03:41 (221.71s)
High-level task being performed: Brew tea
Current scene narration:
  -  Move a mug at the bottom shelf of the cupboard without picking it up.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: []
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [flask, glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: [cover of flask]
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: pick up `mug` from `cupboard.009`

Time: 03:42 (222.72s)
High-level task being performed: Brew tea
Current scene narration:
  -  Move a mug at the bottom shelf of the cupboard without picking it up.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [mug]
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [flask, glass2, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: [cover of flask]
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: put down `mug` to `cupboard.009`

Time: 03:43 (223.67s)
High-level task being performed: Brew tea
Current scene narration:
  -  Move a glass at the second shelf of the cupboard without picking it up, so as to access what's behind it.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: []
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [flask, glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: [cover of flask]
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: pick up `glass2` from `cupboard.009`

Time: 03:44 (224.22s)
High-level task being performed: Brew tea
Current scene narration:
  -  Move a glass at the second shelf of the cupboard without picking it up, so as to access what's behind it.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [glass2]
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [flask, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: [cover of flask]
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: put down `glass2` to `cupboard.009`

Time: 03:44 (224.66s)
High-level task being performed: Brew tea
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: []
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [flask, glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: [cover of flask]
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: pick up `flask` from `cupboard.009`

Time: 03:46 (226.77s)
High-level task being performed: Brew tea
Current scene narration:
  -  Open the cover of the flask by holding the flask using the left hand, holding the cover with the right hand, turning the cover counterclockwise to release it and then lifting it up.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [flask]
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: [cover of flask]
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: pick up `cover of flask` from `mid-air`

Time: 03:47 (227.34s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put the cover on the counter top.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [cover of flask, flask]
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: []
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: put down `cover of flask` to `counter.002`

Time: 03:47 (227.79s)
High-level task being performed: Brew tea
Current scene narration:
  -  Pick up the second cover using the right hand.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [flask]
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, cover of flask, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: []
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: pick up `second cover` from `counter.002`

Time: 03:48 (228.17s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put the second cover on the counter top.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [flask, second cover]
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, cover of flask]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: []
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: put down `flask` to `counter.002`

Time: 03:48 (228.33s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put the second cover on the counter top.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [second cover]
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, cover of flask, flask]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: []
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: put down `second cover` to `counter.002`

Time: 03:50 (230.83s)
High-level task being performed: Brew tea
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: []
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, cover of flask, flask, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: []
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: pick up `small gold color container` from `shelf.003`

Time: 03:55 (235.24s)
High-level task being performed: Brew tea
Current scene narration:
  -  Open the container by holding it with the left hand and then pulling its cover with the right hand.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [small gold color container]
  bin.001: [tissue]
  counter.002: [bag of bagels, container's cover, cover of flask, flask, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: []
  shelf.003: []
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: pick up `container's cover` from `counter.002`

Time: 04:04 (244.74s)
High-level task being performed: Brew tea
Current scene narration:
  -  Put down the empty container on the countertop.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [container's cover, small gold color container]
  bin.001: [tissue]
  counter.002: [bag of bagels, cover of flask, flask, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: []
  shelf.003: []
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: put down `small gold color container` to `counter.009`

Time: 04:05 (245.26s)
High-level task being performed: Brew tea
Current scene narration:
  -  Open the trash bin's lid.
  -  Throw the container's cover in the trash, using the right hand.
Object locations before human action:
  Free Space: [notepad, strainer]
  Human: [container's cover]
  bin.001: [tissue]
  counter.002: [bag of bagels, cover of flask, flask, second cover]
  counter.003: [glass, kettle, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: [small gold color container]
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: []
  shelf.003: []
  sink.001: [bowl, empty pot, left glove, right glove]
  storage.001: []
Human atomic action: put down `container's cover` to `storage.001`
""",
    "response": {
        "is_used": True,
        "explanation": "Step-by-step Chain of Thought reasoning: The object `kettle` is not in the person's hand between 218.07s and 245.26s. However, the user is currently preparing the mug to brew tea, and the kettle is likely boiling water for the tea. Hence, it is being used.",
    }
}

PASSIVE_FORK_LONG = {
    "video_id": "P01-20240203-152956",
    "prompt": """Determine if the object 'fork' is being used during the time period between 00:00 (0.00s) and 00:33 (33.57s).

Analyze the event history before providing your final answer using step-by-step Chain of Thought reasoning.

Event History:
Time: 00:04 (4.61s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up the oven glove from the countertop using the right hand.
Object locations before human action:
  Human: []
  counter.002: [fork, oven glove, plastic spoon, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2]
  mid-air: [unrolled foil]
  oven.001: [tray]
Human atomic action: pick up `oven glove` from `counter.002`

Time: 00:13 (13.05s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Object locations before human action:
  Human: [oven glove]
  counter.002: [fork, plastic spoon, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2]
  mid-air: [unrolled foil]
  oven.001: [tray]
Human atomic action: pick up `tray` from `oven.001`

Time: 00:14 (14.70s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up the tray from the upper shelf of the oven using the right hand holding the oven glove by sliding it out.
Object locations before human action:
  Human: [oven glove, tray]
  counter.002: [fork, plastic spoon, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: put down `tray` to `oven.001`

Time: 00:15 (15.48s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up the tray from the upper shelf of the oven using the right hand holding the oven glove by sliding it out.
Object locations before human action:
  Human: [oven glove]
  counter.002: [fork, plastic spoon, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2]
  mid-air: [unrolled foil]
  oven.001: [tray]
Human atomic action: pick up `tray` from `oven.001`

Time: 00:19 (19.39s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Put the tray on the hob.
Object locations before human action:
  Human: [oven glove, tray]
  counter.002: [fork, plastic spoon, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: put down `tray` to `hob.001`

Time: 00:21 (21.39s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Throw the oven's glove on the countertop using the right hand.
Object locations before human action:
  Human: [oven glove]
  counter.002: [fork, plastic spoon, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: put down `oven glove` to `counter.002`

Time: 00:21 (21.70s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Throw the oven's glove on the countertop using the right hand.
Object locations before human action:
  Human: []
  counter.002: [fork, oven glove, plastic spoon, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: pick up `plastic spoon` from `counter.002`

Time: 00:27 (27.58s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up one meat pie from the tray using the plastic spoon by sliding the spoon under the pie and pulling it up, also using the left hand to break the pie from its neighboring pie.
Object locations before human action:
  Human: [plastic spoon]
  counter.002: [fork, oven glove, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: pick up `pie` from `hob.001`

Time: 00:28 (28.17s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Object locations before human action:
  Human: [pie, plastic spoon]
  counter.002: [fork, oven glove, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: put down `pie` to `hob.001`

Time: 00:33 (33.57s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Pick up a fork from the countertop.
Object locations before human action:
  Human: [plastic spoon]
  counter.002: [fork, oven glove, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: pick up `fork` from `counter.002`
""",
    "response": {
        "is_used": False,
        "explanation": "Step-by-step Chain of Thought reasoning: The object `fork` is not in the person's hand between 4.61s and 33.57s. The activity until 33.57s is about piling meat pies, and none of the action narrations mention before 00:33s or after 00:04s mention using the fork. Hence, it is not being used.",
    }
}

ACTIVE_RIGHTGLOVE_LONG = {
    "video_id": "P01-20240202-171220",
    "prompt": """Determine if the object 'right glove' is being used during the time period between 02:57 (177.84s) and 02:58 (178.20s).

Analyze the event history before providing your final answer using step-by-step Chain of Thought reasoning.

Event History:
Time: 02:57 (177.84s)
High-level task being performed: Prepare candy floss
Object locations before human action:
  Free Space: [strainer]
  Human: []
  bin.001: [tissue]
  counter.002: [container's cover, second cover]
  counter.003: [glass, kettle, notepad, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [bag of bagels, candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [flask, glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: [cover of flask]
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove, right glove]
Human atomic action: pick up `right glove` from `sink.001`

Time: 02:58 (178.20s)
High-level task being performed: Drink some water
Current scene narration:
  -  Touch the glove then release it.
Object locations before human action:
  Free Space: [strainer]
  Human: [right glove]
  bin.001: [tissue]
  counter.002: [container's cover, second cover]
  counter.003: [glass, kettle, notepad, water filter jug]
  counter.004: [ladle, pot, pot3, strainer]
  counter.005: [bottle of washing up liquid, second sponge, sponge]
  counter.006: []
  counter.007: [food processing bin, plug]
  counter.008: [bag of bagels, candy floss machine, disk, knife2, plastic bag, plastic spoon, wooden stick]
  counter.009: []
  cupboard.004: []
  cupboard.008: []
  cupboard.009: [flask, glass2, mug, mug2]
  dishwasher.001: [container, knife, plate, plate2]
  drawer.003: [strainer2]
  hob.001: []
  microwave.001: [scale]
  mid-air: [cover of flask]
  shelf.003: [small gold color container]
  sink.001: [bowl, empty pot, left glove]
Human atomic action: put down `right glove` to `sink.001`
""",
    "response": {
        "is_used": False,
        "explanation": "Step-by-step Chain of Thought reasoning: The object `right glove` is briefly touched by the person during the time period, but is not being used to perform the high-level activity of preparing candy floss. Hence, it is not being used.",
    }
}

ACTIVE_PLATE_LONG = {
    "video_id": "P01-20240203-152956",
    "prompt": """Determine if the object 'plate' is being used during the time period between 00:54 (54.69s) and 00:59 (59.63s).

Analyze the event history before providing your final answer using step-by-step Chain of Thought reasoning.

Event History:
Time: 00:54 (54.69s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - pick up a plate, that's the top of the pile of plates, on the lower shelf of the cupboard.
Object locations before human action:
  Human: []
  counter.002: [fork, oven glove, plastic spoon, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: [plate]
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: pick up `plate` from `cupboard.008`

Time: 00:56 (56.40s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - pick up the plastic spoon from the countertop.
Object locations before human action:
  Human: [plate]
  counter.002: [fork, oven glove, plastic spoon, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: []
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: pick up `plastic spoon` from `counter.002`

Time: 00:57 (57.37s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Move the plate filled with pies to the right of the countertop so that to empty space next to the hob to place the other plate.
Object locations before human action:
  Human: [plastic spoon, plate]
  counter.002: [fork, oven glove, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: []
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: pick up `plate2` from `counter.002`

Time: 00:58 (58.36s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Current scene narration:
  - Move the plate filled with pies to the right of the countertop so that to empty space next to the hob to place the other plate.
Object locations before human action:
  Human: [plastic spoon, plate, plate2]
  counter.002: [fork, oven glove]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: []
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: put down `plate2` to `counter.002`

Time: 00:59 (59.63s)
High-level task being performed: Pick up the second tray from the oven, pile the meat pies on two plate and cover one of them using foil paper
Object locations before human action:
  Human: [plastic spoon, plate]
  counter.002: [fork, oven glove, plate2]
  counter.008: [foil wrap]
  counter.009: [foil2]
  cupboard.008: []
  drawer.002: [box of foil wrap]
  hob.001: [pie, pie2, tray]
  mid-air: [unrolled foil]
  oven.001: []
Human atomic action: put down `plate` to `counter.002`
""",
    "response": {
        "is_used": True,
        "explanation": "Step-by-step Chain of Thought reasoning: The object `plate` is in the person's hand while the person is piling meat pies. The plate is meaningfully contributing to the high-level activity of piling the meat pies. Hence, it is being used.",
    }
}