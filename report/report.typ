// ============================================================
//  EEE/EIE Y2 Smart Grid Project Report
//  Group: Watt's Up
//  Imperial College London, June 2026
// ============================================================

// ---------- Document metadata ----------
#set document(
  title: "EEE/EIE Y2 Smart Grid Project",
  author: "Watt's Up",
)

// ---------- Page setup ----------
#set page(
  paper: "a4",
  margin: (x: 2.5cm, y: 2.5cm),
)

// ---------- Text & paragraph ----------
#set text(
  font: "New Computer Modern",
  size: 11pt,
  lang: "en",
)
#set par(justify: true, leading: 0.65em)

// Hyperlinks (e.g. bibliography URLs) render in a muted blue, no underline.
// Only affects `link` elements; figure/section cross-references and citation
// numbers are `ref`/`cite` elements and stay black.
#show link: set text(rgb("#1a3e7a"))

// ---------- Tables: consistent, professional style ----------
// Dark-blue header row with white bold text, light zebra striping on the body,
// horizontal hairlines only (no vertical rules) and generous padding. The
// protable() wrapper keeps each table on a single page so it never splits
// across a page boundary.
#let _tbl-blue  = rgb("#23457d")
#let _tbl-zebra = rgb("#eef2f7")
#let _tbl-line  = rgb("#cbd3df")

#set table(
  inset: (x: 7pt, y: 6pt),
  stroke: (x, y) => (
    left: none, right: none,
    top: 0.5pt + _tbl-line,
    bottom: if y == 0 { 0.9pt + _tbl-blue } else { 0.5pt + _tbl-line },
  ),
  fill: (x, y) => if y == 0 { _tbl-blue } else if calc.odd(y) { _tbl-zebra } else { white },
)
#show table.cell: set text(size: 10pt, hyphenate: false)
#show table.cell: set par(justify: false)
#show table.cell.where(y: 0): set text(fill: white, weight: "bold")

#let protable(..args) = block(breakable: false, table(..args))

// ---------- Heading numbering & styling ----------
#set heading(numbering: "1.1")

#show heading.where(level: 1): it => [
  #counter(figure.where(kind: image)).update(0)
  #set text(size: 16pt, weight: "bold")
  #v(0.6em)
  #it
  #v(0.3em)
]

// ---------- Figure numbering by section (1.1, 1.2, 2.1, ...) ----------
#set figure(numbering: n => numbering("1.1", counter(heading).get().first(), n))
#show heading.where(level: 2): it => [
  #set text(size: 13pt, weight: "bold")
  #v(0.4em)
  #it
  #v(0.2em)
]
#show heading.where(level: 3): it => [
  #set text(size: 11pt, weight: "bold", style: "italic")
  #it
]

// ============================================================
//  Cover Page (with Abstract)
// ============================================================
#set page(numbering: none)

#align(center)[
  #v(1.2cm)
  #text(size: 24pt, weight: "bold")[EEE/EIE Y2 Smart Grid Project]

  #v(0.7cm)
  #text(size: 18pt, weight: "bold")[Group: Watt's Up]

  #v(1.2cm)
  #text(size: 12pt)[
    Dzuldiniy Hussain Bin Dzulkeflee (CID) \
    Chun Wen Ooi (CID) \
    Wei Zen Ooi (02614796) \
    Fang Nan Tan (CID) \
    Hong Zhe Tan (02562503) \
    Yong Zhi Tong (02581094) \
    Yi Da Wu (02567507)
  ]

  #v(0.8cm)
  #text(size: 13pt)[Imperial College London]
  #v(0.15cm)
  #text(size: 13pt)[June 2026]
]

#v(1cm)

// Abstract on cover
#align(center)[
  #text(size: 14pt, weight: "bold")[Abstract]
]
#v(0.3cm)

The Smart Grid was developed as a DC microgrid built from four cooperating power converter modules. It needed to balance generation, storage, and load on a shared 10V bus while maximising earnings or minimising expenses through grid import, export and supercapacitor charge or discharge. These converters, with independent SMPS topologies, contributed regulated current flows managed by the central coordinator for optimal power dispatch. The electrical limits of a 12V primary supply and a 10V bus with ±0.1V droop band were observed, allowing each module to operate autonomously through bus voltage signals. Architecture included a microcontroller on every module, INA219 and SPI ADC telemetry, and a user interface for operator monitoring. A 3D printed chassis housed the SMPS boards in their optimal positions for airflow and mechanical protection. The microgrid was powered by a 12V bench supply, with each Pico W regulating a local 3.3V rail for logic and sensors.

#v(0.5cm)
#align(center)[
  #text(size: 10pt, style: "italic")[Word count: #text(weight: "bold")[XXXX]]
]

#pagebreak()

// ============================================================
//  Table of Contents (roman numerals)
// ============================================================
#set page(numbering: "i")
#counter(page).update(1)

#outline(
  title: [Contents],
  indent: auto,
  depth: 3,
)

#pagebreak()

// ============================================================
//  Main Body (arabic numerals, restart at 1)
// ============================================================
#set page(numbering: "1")
#counter(page).update(1)


// ----- 1. Project Objectives & Management (~500 words) ------
= Project Objectives & Management

== Project Objectives

The project shall deliver a four-module DC microgrid that cooperatively regulates a shared 10V bus across PV generation, supercapacitor storage, a bidirectional grid interface and a programmable LED load. The control system shall autonomously dispatch power between modules to minimise net cost under a time-varying tariff. The complete prototype shall be evaluated on demo day, 18 June 2026, against a published price-and-load scenario.

== Project Management System & Temporal Organisation

Coordinating a seven-member hardware and software team across a five-weeks delivery window required tooling that off-the-shelf platforms could not provide as a single integrated system. Rather than stitching together Notion, Trello, Microsoft Teams and ChatGPT, each of which solves only a fragment of the problem and none of which share state, a bespoke AI-powered Project Management System (PMS) was self-coded for the project. Every layer of the frontend, backend, AI pipeline and database schema was purpose-built around the rhythm of the team and the constraints of the brief.

#figure(
  image("images/pms_dashboard.png", width: 100%),
  caption: [PMS dashboard: countdown, budget, stats and todo.],
) <fig:pms-dashboard>

The platform is structured around four modules. A live operational dashboard (@fig:pms-dashboard) provides the project's situational awareness layer. An automated meeting transcript module (@fig:pms-transcript) records, transcribes and structures every meeting into attendee lists, discussion summaries and extracted action items, eliminating the historical note-taker tax and providing an unambiguous decision record. An AI-driven article and documentation generator named Aria (@fig:pms-article) produces project-specific technical writing such as component-selection notes and lab write-ups, grounded in the team's own document base. A Retrieval-Augmented Generation (RAG) project chat (@fig:pms-rag) ties everything together by indexing meeting minutes, Aria articles, the GitHub firmware repository, datasheets, test results and curated project memory, so that any team member can self-serve evidenced answers without bottlenecking a senior peer.

#figure(
  image("images/pms_transcript.png", width: 98.5%),
  caption: [Meeting transcript module.],
) <fig:pms-transcript>

#figure(
  image("images/pms_article.png", width: 98.5%),
  caption: [Aria article generator.],
) <fig:pms-article>

#figure(
  image("images/pms_rag_chat.png", width: 98.5%),
  caption: [RAG project chat with cited sources.],
) <fig:pms-rag>

Because every module was written in-house, outputs of one feed directly into the next without manual export. A transcribed meeting immediately enriches the RAG corpus, an Aria article updates the dashboard document count, and a new task synchronises across the calendar and the email reminder service. Temporal organisation is enforced by the countdown and calendar views, which together render the 18 June 2026 demo day as a daily, visceral constraint rather than an abstract deadline. The cumulative effect across the project window has been faster decision turnaround, fewer duplicated discussions, and zero overspend events against the £60 budget.

Beyond the four core modules, several additional features were built specifically to eliminate single points of failure in the team's data and operational continuity (@fig:pms-extras). A shared calendar with a Gantt-style timeline consolidates every milestone, dependency and submission deadline so that schedule knowledge does not live in any one person's head. A project image gallery centralises lab photography that would otherwise be scattered across personal phones and never recovered. A test results module captures raw measurement data with built-in charting, removing the spreadsheet-on-one-laptop antipattern that historically destroys reproducibility. Finally, lightweight personalisation through the team buddy selector keeps the platform somewhere team members actively want to log into, sustaining the upstream coordination benefits on which every other module depends.

#figure(
  grid(
    columns: 2,
    rows: 2,
    gutter: 6pt,
    image("images/pms_calendar.png", width: 100%),
    image("images/pms_images.png", width: 100%),
    image("images/pms_test_results.png", width: 100%),
    image("images/pms_buddies.png", width: 100%),
  ),
  caption: [Calendar, image gallery, test results, and buddy selector.],
) <fig:pms-extras>

#pagebreak()


// ----- 2. System Architecture & Key Design Decisions (~1500) -
= System Architecture & Key Design Decisions

System architecture decisions fix the boundary conditions for every subsequent SMPS, control loop and measurement choice. This section walks through the role of each module, the topology that wires them together, and the rationale behind the bus voltage, supply voltage, coordination scheme and inter-module communication.

== Module Roles

The system comprises five SMPS modules cooperating on a shared 10V DC bus. Each module implements a specific role with a topology and control mode chosen to match it.

#protable(
  columns: (auto, auto, auto, auto, auto),
  align: left + horizon,
  [*Module*], [*External component*], [*Topology*], [*Control*], [*Role on the bus*],
  [Import SMPS], [12V grid PSU], [Buck], [CV, droop at 9.9V], [Sources current when bus < 9.9V],
  [Export SMPS], [Sink resistor], [Buck], [CV, droop at 10.1V], [Sinks current when bus > 10.1V],
  [PV SMPS], [6.23V PV panel], [Boost], [MPPT], [Harvests panel power into bus],
  [Supercap SMPS], [10.5 to 17.5V supercap], [Bidirectional buck/boost], [CC, commanded], [Stores or releases on command],
  [LED Load SMPS], [3V LED module], [Buck (internal)], [CC], [Drives the LED load],
)

The two grid-facing modules share a common topology (synchronous buck) and a common control law (droop), differing only in their droop setpoints. This is what creates the dead-band around the nominal bus voltage discussed in Section 2.5. The Supercapacitor SMPS departs from droop entirely and runs as a commanded current source, which allows the economic algorithm in Section 9 to use storage as temporal arbitrage rather than as a passive load-sharing element. The LED Load SMPS is internally managed and exposes only its bus-side power draw to the rest of the system.

All four bidirectional modules are physically the same board, the synchronous half-bridge of @fig:smps-stage, carrying a 100µH inductor and a 100mΩ shunt on the Port B side. The distinct roles in the table above are realised entirely by how each board's ports are connected and how its buck/boost switch is set, not by different hardware, so the per-module sections that follow refer back to this single power stage rather than redrawing it.

#figure(
  image("images/bidirectional_power_stage.png", width: 100%),
  caption: [Bidirectional SMPS power stage, common to all four modules @clemow_smps.],
) <fig:smps-stage>

== Overall Microgrid Topology

The complete system is shown in @fig:arch-block. External components sit at the top of the diagram, each connected through their respective SMPS module to the shared 10V DC bus. Every SMPS is driven by a dedicated Pico W microcontroller running its local control loop. A React backend server polls an Azure-hosted web service every 5 seconds for the current demand, price and irradiance signals, computes the dispatch decision documented in Section 9, and pushes setpoint commands to the modules through the ESP32 coordinator. The operator-facing dashboard renders telemetry from the same backend.

#figure(
  image("images/arch_block.png", width: 100%),
  caption: [Smart Grid system architecture and power flow.],
) <fig:arch-block>

Three properties of this topology are referenced repeatedly in later sections. First, every SMPS module is fully autonomous in its bus-regulation role: it requires only its local V_bus measurement to act, and the backend provides only setpoint commands and economic context. Second, all demo-day power measurements occur at the bus, never at the individual SMPS terminals. Third, the supercapacitor is the only element capable of storing energy across timescales longer than the bus capacitance, which makes its commanded behaviour central to the economic optimisation in Section 9.

== Bus Voltage Choice: 10 V Nominal, ±0.1 V Droop Band

The 10V nominal bus value is the smallest round-number voltage that simultaneously sits below the supercapacitor charge window, sits above the PV panel open-circuit voltage of approximately 8.5V, and leaves enough headroom for a buck-derived import from a 12V supply (justified in Section 2.4). Setting the bus higher would increase switching stress on every buck module without improving any system property. Setting it lower would force the supercapacitor window to a less convenient range and increase the PV boost ratio. Ten volts is also a natural target for hobbyist instrumentation.

Each droop-controlled module follows a local linear control law of the form

$ I_("module") = (V_("set") - V_("bus")) / R_("droop") $

with sign and saturation chosen by the module's role. The droop resistance $R_("droop")$ is sized so that the module current saturates at its rated maximum exactly at the edge of the ±0.1V band. This bounds the steady-state bus error to ±0.1V at full load, which is ±1% of nominal and tight enough to be a stiff bus for all downstream loads.

A critical consequence of taking demo-day measurements on the bus itself is that conversion losses on different paths are weighted asymmetrically in the score. For the LED Load SMPS and the Export SMPS, the losses lie between the bus and the destination, so the bus delivers $P_("destination") + P_("losses")$ and the metric counts the sum as either load or export. SMPS efficiency on those two paths therefore does not affect the score, and the modules can be sized for cost or simplicity rather than peak efficiency. For the Import SMPS the losses lie between the 12V supply and the bus measurement point, so the bus receives only $P_("grid") - P_("losses")$. Every watt lost in the import path is grid energy that does not appear at the bus, directly degrading the economic score. Import SMPS efficiency therefore receives disproportionate attention in Section 3 and Section 11.

== PSU Voltage Rationale: 12 V

The choice of 12V for the primary supply is driven by efficiency. For a synchronous buck converter, the steady-state conduction loss summed across both switches is

$ P_("cond") = D dot I_("rms")^2 dot R_("ds,on,HS") + (1 - D) dot I_("rms")^2 dot R_("ds,on,LS") $

When the high-side and low-side MOSFETs are matched, $R_("ds,on,HS") = R_("ds,on,LS") = R_("ds,on")$, and the duty cycle terms collapse:

$ P_("cond") = I_("rms")^2 dot R_("ds,on") $

independent of D and therefore independent of $V_("in")$. Switching loss, in contrast, does not collapse:

$ P_("sw") approx 1/2 dot V_("in") dot I_("load") dot (t_r + t_f) dot f_("sw") + 1/2 dot C_("oss") dot V_("in")^2 dot f_("sw") $

Every term scales with $V_("in")$ or $V_("in")^2$. Inductor ripple also shrinks as $V_("in")$ approaches $V_("bus")$:

$ Delta I_L = (V_("in") - V_("bus")) dot D dot T / L $

which reduces inductor RMS current and copper loss as a second-order benefit. The net result is that import SMPS efficiency rises as $V_("in")$ is reduced toward $V_("bus")$, but only weakly: with matched synchronous FETs the dominant conduction term is independent of $V_("in")$, leaving the modest switching term as the only input-voltage-dependent loss.

The binding constraint is therefore not efficiency but dropout. A buck produces $V_("bus")$ at a duty $D = V_("bus") / V_("in")$, which tends to unity as $V_("in")$ approaches $V_("bus")$, yet a real converter cannot reach $D = 1$: a minimum switch off-time, gate-driver refresh requirements, and the controller's maximum-duty clamp all hold the duty below unity. With a maximum duty of roughly 0.9, regulation is lost once $V_("in")$ falls below about $V_("bus") / 0.9 approx 11$V, where the output begins to sag below target. Fixing $V_("in") = 12$V leaves comfortable margin above this floor and coincides with the standard lab bench-supply rail; the marginal efficiency gain from lowering $V_("in")$ further does not justify eroding that margin.

@fig:buck-vin-eff plots this loss model at a fixed 10V bus and 1.5A load. Across the usable 11V to 15V range the modelled efficiency is nearly flat: total loss shifts by only a few tens of milliwatts, around 0.2% of the delivered power, because conduction loss is constant and only the small switching term tracks $V_("in")$. The sharp collapse at the left of the plot is not a loss effect but the dropout region described above, where the converter can no longer regulate, so it marks the unusable input range rather than an inefficient one. The chosen 12V point sits on the flat plateau with comfortable margin above that floor.

#figure(
  image("images/buck_vin_efficiency.png", width: 100%),
  caption: [Modelled buck efficiency and loss split versus input voltage.],
) <fig:buck-vin-eff>

A confirmation experiment is flagged in Section 12 (Future Work): sweep $V_("in")$ from 11V to 14V at fixed $V_("bus") = 10$V and measure import SMPS efficiency. The expectation, given the analysis above, is a shallow monotonic rise as $V_("in")$ falls toward 11V, ending in a steep efficiency cliff once dropout kicks in.

== Coordination Scheme: Symmetric Droop vs Mutex Arbitration

Two architectures were considered for coordinating the bus. Mutex arbitration assigns control to exactly one module at a time, with a central coordinator switching modes (PV-controlled, grid-controlled, supercap-controlled) as conditions change. Symmetric droop instead allows every module to act simultaneously, each modulating its own current from a local V_bus measurement relative to its setpoint.

Mutex arbitration produces tighter bus regulation in steady state because exactly one feedback loop is active at a time. However, it places the inter-module communication channel inside the safety-critical bus-regulation loop: if comms drop or the coordinator stalls, every module loses its reference and the bus collapses. Mode transitions also generate voltage transients as the active controller hands over.

Symmetric droop avoids both failure modes. Each module's control loop is local and continuous, requiring only its own bus measurement, so a comms failure degrades the economic optimisation in Section 9 but does not threaten bus stability. The droop curves blend rather than switch, eliminating handover transients, and modules can join or leave the bus arbitrarily without reconfiguring a coordinator. The cost is a small steady-state V_bus error, bounded to ±0.1V by design as derived in Section 2.3.

Symmetry is enforced by mirroring the import and export setpoints about the 10V nominal:

$ V_("set,import") = 9.9 "V" quad quad V_("set,export") = 10.1 "V" $

This creates a dead-band $V_("bus") in [9.9, 10.1]$ V in which neither grid-facing module acts. Inside the dead-band the bus is held by the PV harvester and the supercapacitor, which is precisely the configuration the algorithm in Section 9 seeks to maximise (no grid interaction means no cost incurred). Outside the dead-band the system gracefully falls back to grid import or export with no explicit mode-change logic. The droop curves for all five modules are shown in @fig:droop-curves.

#figure(
  image("images/droop_curves.png", width: 85%),
  caption: [Droop curves: module current versus bus voltage.],
) <fig:droop-curves>

@fig:busbar-deadband illustrates the same coordination over a load cycle. The bus floats inside the dead-band while supply and demand match, is pulled below 9.9V (where the grid module begins to source) when load exceeds local generation, and is pushed above 10.1V (where the export module begins to dissipate) when generation exceeds load. The small steady-state offsets from each setpoint are the droop error, and the system moves between the three regimes with no mode-change logic.

#figure(
  image("images/busbar_deadband.png", width: 100%),
  caption: [Bus voltage and converter currents across import, dead-band and export.],
) <fig:busbar-deadband>

Choosing droop over mutex maps directly onto the single-point-of-failure mitigation theme introduced in Section 1.2. The communication layer becomes advisory, not safety-critical, and is described next.

== Communication Protocol

The communication protocol is provisional and described here at the architectural level only. A central ESP32 module hosts a WiFi access point joined by every Pico W. Setpoint commands, telemetry and economic context flow over this link in JSON-framed messages. The React backend sits one layer above the ESP32, polling the Azure-hosted web service every 5 seconds for current demand, price and irradiance signals, computing the dispatch decision (Section 9), and pushing setpoint updates back down to the modules. The 5-second cadence balances Azure rate-limit considerations against the natural timescale of the demand-and-price signal. The dashboard frontend renders telemetry from the same backend without participating in control.

Crucially, the protocol layer sits outside the safety-critical bus-regulation loop. Comms loss leaves every module operating against its last commanded setpoint with its local droop or CC law intact, so the bus continues to regulate. Final framing details (transport, framing, retry policy, error handling) are deferred until module integration testing in Section 11.

#pagebreak()


// ----- 3. PV SMPS (~1000 words) ------------------------------
= PV SMPS

== Design & Simulation

=== Topology Selection

The PV panel is an 8W nominal device with a nominal open-circuit voltage of approximately 8.5V and a short-circuit current of approximately 1.0A, measured at about 7.9V open-circuit under the solar emulator. Its maximum power point sits near 6.4V at full irradiance and falls toward 5.7V in low light, as the measured I-V and P-V sweeps in @fig:pv-iv show. Each curve was taken by stepping the load current and recording the panel voltage at one of seven emulator dimmer settings. Because the maximum-power voltage (around 6V) is below the 10V bus, energy can only be delivered to the bus by stepping the panel voltage up, so the module runs as a boost converter.

#figure(
  image("images/pv_iv_measured.png", width: 100%),
  caption: [Measured PV panel I-V and P-V curves with the MPP locus.],
) <fig:pv-iv>

The boost direction is consistent with the module's hard constraint that Port A must sit above Port B for any energy transfer (the shared power stage is shown in @fig:smps-stage). The panel is wired to Port B (the lower, variable voltage) and the bus to Port A (the fixed 10V), so current flows from Port B to Port A and the panel always satisfies $V_("A") > V_("B")$. The BU/BO switch is set to BOOST, which also routes the on-board support rail (Pico, current sensor, gate drivers) from Port B; during bench work the Pico is additionally USB-powered, so panel collapse does not reset the controller. Unlike the grid and export buck modules, the boost PWM is not inverted: the firmware writes the duty directly rather than the `65536 - pwm_out` form the buck modules require.

Current is sensed by the INA219 across the 0.10 ohm shunt at Port B. The shunt is physically wired in the Port A to Port B sense direction, so the firmware negates the reading: a positive inductor current then corresponds to panel-to-bus boost flow. The control structure is a cascaded pair, an outer voltage PI that servoes the panel voltage to the commanded $V_("mpp")$ and an inner current PI that drives the duty, with the operating point set by whichever MPPT strategy is active.

=== MPPT Strategy: Lookup Table vs P&O

Three approaches for maximum power point tracking were considered: a static constant-voltage operating point, an irradiance-indexed lookup table, and online Perturb and Observe (P&O) gradient ascent. The constant-voltage approach was discarded because the panel's $V_("mpp")$ shifts with both irradiance and temperature; a single $V_("mpp")$ setpoint loses 10 to 20% of available harvest in low light. The two remaining methods were prototyped against each other and made user-selectable from the host dashboard so that Section 3.3 can present a quantitative comparison rather than commit to a single shipped strategy.

The lookup table method exploits the externally available irradiance signal. The PV module fetches the current sun value from the Azure-hosted `/sun` endpoint every five seconds, normalises to a fraction in $[0, 1]$, and interpolates against a piecewise-linear $V_("mpp")$ versus irradiance table built from the characterisation sweeps of @fig:pv-iv. The extracted maximum-power points are plotted against irradiance in @fig:pv-vmpp, and these values, ranging from 5.65V at 10% irradiance to 6.43V at full sun, are exactly the entries loaded into the firmware table. Settling is immediate because the new $V_("mpp")$ is commanded as a step input to the existing outer voltage PI. The costs are the prior characterisation effort and the dependency on the web link remaining alive; if the link drops, the firmware degrades gracefully by holding the last good irradiance value rather than commanding an arbitrary fallback.

#figure(
  image("images/pv_vmpp_irradiance.png", width: 78%),
  caption: [Measured Vmpp and Pmax versus irradiance: the MPPT lookup table.],
) <fig:pv-vmpp>

P&O makes no assumption about $V_("mpp")$. The algorithm perturbs the commanded $V_("mpp")$ by a small fixed step, measures the resulting power averaged over a settling window, compares to the previous window, and either keeps or reverses the perturbation direction. With no irradiance sensor required, P&O is inherently more robust against web link outages or unmodelled panel behaviour, at the cost of continuous oscillation around the peak and slower convergence after rapid irradiance steps. The literature on P&O cautions that naive implementations using a single instantaneous power sample per perturbation collapse into noise-driven random walks when the per-sample noise exceeds the curvature of the $P(V_("mpp"))$ surface near the peak; the bench-noise floor (Section 3.2) made this an active concern that shaped the implementation.

Implementing both, rather than committing to one, is driven by the marking rubric's emphasis on quantitative evaluation. Shipping both also leaves the system robust to single-method failure: a web link outage degrades from web-lookup to fixed-mode with no firmware change.

=== LTspice / Python Simulation

== Testing & Implementation

Three implementation concerns dominated bringing the PV SMPS up on the bench: noise on the measured panel power that masked operating-point differences, robust P&O behaviour against that noise, and a clean framework for comparing the two MPPT modes during evaluation. Each is described in turn.

=== Bench Noise Treatment

Raw $P_("panel") = V_("panel") dot I_("L")$ telemetry at the 1 kHz control tick rate showed several-hundred-milliwatt peak-to-peak jitter at steady state, dominating the mode-to-mode harvest differences the comparison in Section 3.3 needed to resolve. Three sources contributed. Single-sample Pico ADC noise on the $V_("panel")$ reading walks several LSBs sample to sample due to clock and supply coupling; one LSB at 12-bit resolution after the divider scale is approximately 16 mV. Switching ripple at 100 kHz aliases into the 1 kHz sample stream because the tick is unsynchronised with the PWM cycle. The INA219 was running at its template default of 8-sample internal averaging, with only modest attenuation of the shunt-side ripple.

A three-layer fix was applied. The Pico ADC is oversampled four times per tick on $V_("panel")$ and $V_("bus")$ reads, costing roughly 10 us per call and removing the bulk of the ADC walk noise. The INA219 CONFIG register is reprogrammed to 0x1E67, raising both the bus and shunt ADCs to 16-sample 12-bit averaging at 8.51 ms conversion time. A first-order exponential moving average with coefficient $alpha = 0.05$ (time constant approximately 20 ms, corner approximately 8 Hz) is applied in software on top of the hardware-averaged readings. The full derivation of this filter chain and its application across modules is given in Section 7.3.

The filtered values feed only the dashboard display and the P&O comparison; the inner current PI and the safety guards continue to consume the raw single-sample readings so that the original loop tuning is unchanged and trip response remains instantaneous.

=== P&O Implementation

P&O was implemented with a two-timescale structure. The outer voltage PI continues to track the commanded $V_("mpp")$ at 100 Hz; perturbations to that command occur on a 300 ms cadence ($T_("dwell")$). The cadence is roughly five times the outer-loop settling time so that the power measured at the end of a dwell reflects the new steady-state operating point rather than the PI transient. Power for the comparison is the filtered $V_("panel,lp") dot I_("L,lp")$ accumulated only over the second half of each dwell window and then averaged. The two-stage filtering (EMA followed by dwell average) brings the per-comparison noise floor below 10 mW, well under the curvature of the $P(V_("mpp"))$ surface near the peak.

A direction-flip rule with a dead-band prevents the three-point oscillation around the peak from degenerating into a noise-driven random walk. If the dwell-averaged power decreased by more than $epsilon = 20$ mW since the previous dwell, the perturbation direction is reversed; otherwise the previous direction is held. The commanded $V_("mpp")$ is hard-clamped to the 5.0 V to 7.0 V window so that an algorithm fault cannot walk the operating point off into open-circuit or short-circuit territory. On entry to P&O mode the state is reseeded from the last commanded fixed-mode $V_("mpp")$, avoiding a stale or possibly faulty prior value.

=== Mode Comparison Support

To make MPPT mode comparison tractable on bench equipment, a true three-second block average of $P_("panel")$ was added to the firmware telemetry, restarting whenever the MPPT mode is changed from the dashboard. The operator procedure becomes "fix the panel under stable light, select mode A, wait three seconds, read the number, select mode B, wait three seconds, read the number". This separates the question of which algorithm finds a higher operating point (resolved by the averaged numbers) from the question of how noisily the operating point is tracked (resolved by inspecting the live trace). The same block-average pattern is reused in Section 4 and Section 5 for the supercap and grid efficiency tests.

== Evaluation & Optimisation

Two evaluation axes are reported for the PV SMPS: MPPT mode comparison, and SMPS conversion efficiency.

=== MPPT Mode Comparison

Each MPPT mode is tested across the lookup table's irradiance range using the lab dimmer to set fractional sun at 25%, 50%, 75% and 100%. At each setting the three-second block-averaged $P_("panel")$ is recorded in fixed mode (commanded at the table's $V_("mpp")$), web mode (tracking the live sun signal), and P&O mode (started from the same $V_("mpp")$ seed). The primary metric is steady-state delivered power; the secondary metric is convergence time, defined as the time from a mode switch until $P_("panel")$ enters and stays within a ±5% band of the final value.

The expected outcome is that web-lookup and P&O converge to the same delivered power within bench noise at the four characterised irradiances, because P&O hunts to the same peak the table is built from. The interesting comparison is therefore off the table's characterised points: at irradiance values between the table entries (where the interpolation is approximate) and at panel temperatures away from characterisation conditions (where the table is open-loop and P&O is closed-loop). P&O is expected to win on convergence speed only if the perturbation cadence is reduced from its conservative 300 ms; future work covers the cadence sweep.

=== SMPS Efficiency Characterisation

PV conversion efficiency is defined as $eta_("PV") = P_("bus,out") / P_("panel,in")$. The pre-loss quantity $P_("panel,in") = V_("panel") dot I_("L")$ is directly available from the firmware because both factors are Port B side measurements on the boost topology, where the inductor current equals the input current. The post-loss quantity $P_("bus,out") = V_("bus") dot I_("bus,out")$ is not directly available: the shunt sits between the inductor and Port B per the lab schematic, so Port A (the bus side) is uninstrumented on every bidirectional module.

Three approaches were considered for measuring $P_("bus,out")$. The first was an automated test using the supercapacitor module as a calibrated load: with the cycle-test round-trip efficiency $eta_("cap")$ known (Section 4.3), the cap-side stored energy rate $C dot V_("cap") dot (d V_("cap")) / (d t)$ divided by $eta_("cap,charge")$ gives the bus-side power into the cap, which equals $P_("bus,out")$ when no other module is sourcing or sinking. The second was using the LED Load SMPS bus draw, after a one-time bench characterisation of the LED module's own efficiency $eta_("LED")$. Both automated approaches cascade two independently measured efficiencies, compounding their ±1 to 2% characterisation errors and introducing a dependency on the calibration operating point matching the test operating point. The third was a manual bench measurement using a digital multimeter (DMM) placed in series with the PV-to-bus wire, giving $I_("bus,out")$ directly.

For the demo-day characterisation the third approach was chosen. The decision is justified by the marking rubric's evaluation criterion that rewards quantitative evidence and informative visual presentation: a smaller number of high-confidence ground-truth measurements yields a more defensible $eta_("PV")$ curve than a larger number of cascaded automated measurements. The chosen sweep covers two axes. The bus-voltage axis is swept across seven points from 7.1 to 10.2 V in 0.5 V steps, deliberately wider than the import/export dead-band of Section 2.5 so that the duty-cycle dependency is captured across the full physically reachable range rather than just the cluster around 10 V. The irradiance axis adds the 25%, 50% and 75% lab-dimmer settings to complement the 100% setting used here, with the optimal bus voltage from the first sweep held fixed. At each grid point the operator reads $P_("panel")$ off the dashboard, reads $I_("bus,out")$ off the DMM, computes $P_("bus,out") = V_("bus") dot I_("bus,out")$ and reports $eta_("PV") = P_("bus,out") / P_("panel")$. The bus-voltage axis was completed at 100% irradiance and is reported in Section 3.3.3 below; the three lower-irradiance points are scheduled for the next test session.

A subsequent automation step would replace the manual DMM measurement with the cap-as-calibrated-load approach: the first DMM sweep then serves as a single calibration step, after which characterisation runs can be triggered from the dashboard without bench instrumentation.

=== Measured SMPS Efficiency

@fig:pv-eta-measured and the table below present the bus-voltage sweep at 100% irradiance, with the panel pinned at its MPP ($V_("panel") approx 6.23$ V, $P_("panel") approx 2.3$ W). The seven points span $V_("bus") = 7.1$ V to $10.2$ V in 0.5 V steps, giving a corresponding boost duty cycle $D = 1 - V_("panel") / V_("bus")$ that walks from 0.13 to 0.39. Efficiency lies between 95.0% and 98.7%, with a mean of 97.3% and a standard deviation of 1.3%.

#protable(
  columns: (auto, auto, auto, auto, auto, auto),
  align: center + horizon,
  [*$V_("bus")$ (V)*], [*$V_("panel")$ (V)*], [*Duty $D$*], [*$P_("panel")$ (W)*], [*$P_("bus")$ (W)*], [*$eta_("PV")$ (%)*],
  [7.11], [6.22], [0.13], [2.42], [2.30], [95.0],
  [7.61], [6.23], [0.18], [2.34], [2.25], [96.2],
  [8.11], [6.23], [0.23], [2.25], [2.19], [97.3],
  [8.61], [6.23], [0.28], [2.28], [2.25], [98.7],
  [9.12], [6.23], [0.32], [2.30], [2.26], [98.3],
  [9.61], [6.23], [0.35], [2.45], [2.40], [98.0],
  [10.21], [6.23], [0.39], [2.26], [2.21], [97.8],
)

#figure(
  image("images/pv_efficiency_measured.png", width: 100%),
  caption: [Measured PV SMPS efficiency versus bus voltage at 100% irradiance.],
) <fig:pv-eta-measured>

The scatter is consistent with the ±0.01 A resolution of the DMM at the approximately 0.23 A operating current, where one count is about 0.4% of $eta_("PV")$. The variation across the bus range does not reveal a strong dependency on bus voltage: the lowest reading at 7.1 V (95.0%) is plausibly a single-point dip rather than a trend, since the remaining six points sit between 96.2% and 98.7% with no clean monotonic ordering against $V_("bus")$. The duty cycle implied by the sweep, $D = 0.13$ to $0.39$, places every operating point on the flat high-efficiency plateau of the boost converter's $eta$-versus-$D$ characteristic.

This is consistent with the published shape for boost converters, where efficiency stays high and approximately flat across low and moderate duty cycles before falling off in CCM at high duty as conduction loss scales with the larger inductor RMS current. Fig. 5 of @navamani_iccpct2015, reproduced in @fig:pv-eta-ref, shows this characteristic in both DCM and CCM: a flat plateau across $D$ approximately 0.1 to 0.6 and a sharp CCM cliff beyond $D approx 0.7$. The hardware in fact cannot reach that cliff regime at all. With the panel pinned at its 6.23 V MPP, the boost duty $D = 1 - V_("panel") / V_("bus")$ requires $V_("bus") > 20.8$ V to hit $D = 0.7$, which exceeds the 17.5 V supercapacitor window ceiling and the board's rated operating range. The maximum reachable duty cycle at the 17.5 V bus ceiling is $D_("max") = 1 - 6.23 / 17.5 = 0.64$, still well clear of the cliff. The measured plateau therefore represents the converter's behaviour across its entire physically reachable operating space, and no high-duty efficiency derating is anticipated for demo-day operation.

#figure(
  image("images/pv_efficiency.png", width: 78%),
  caption: [Boost efficiency versus duty cycle in DCM and CCM, from Fig. 5 of @navamani_iccpct2015.],
) <fig:pv-eta-ref>

The irradiance axis is the principal outstanding item for this evaluation. The bus-voltage axis having shown a flat $eta_("PV")$ across the operating range at 100% irradiance, the next test session adds the 25%, 50% and 75% dimmer settings at the cluster of best-efficiency bus voltages to capture the second-order dependency on operating power.

#pagebreak()


// ----- 4. Supercapacitor SMPS (~1000 words) ------------------
= Supercapacitor SMPS

== Design & Simulation

=== Boost Topology and Boot-with-Empty-Cap Rationale

The supercapacitor bank is the only variable-voltage element on the storage side, swinging between 10.5V when depleted and 17.5V when full. The same Port A above Port B transfer rule that fixed the PV topology dictates the port assignment here (the shared power stage is @fig:smps-stage): the cap is the higher and variable rail and must sit on Port A, with the fixed 10V bus on Port B. Energy then flows from bus to cap (Port B to Port A) when charging and from cap to bus (Port A to Port B) when discharging, so the module is genuinely bidirectional rather than a one-way source or sink.

The BU/BO switch is set to BOOST, which is the load-bearing decision for robustness. With BOOST selected, the on-board support circuitry draws from Port B, the bus, which is always energised by the grid and PV modules. The board therefore boots and stays alive even when the cap is fully empty at 0V. The alternative BUCK setting would power the support rail from Port A, the cap, and would brick the controller whenever the cap fell below the 6V to 7V minimum support voltage, which is precisely the depleted state from which the system most needs to recover. As with the PV boost module, the PWM is not inverted. The current sign convention follows the PV module: a positive inductor current means charging (bus to cap), a negative current means discharging (cap to bus), and the dashboard command $i_("cmd")$ is signed accordingly.

=== Operating Window 10.5 to 17.5 V

The usable voltage window falls out of three hard limits, illustrated against the stored-energy curve in @fig:supercap-energy. The ceiling $V_("cap,max") = 17.5$V is the SMPS port limit and sits comfortably under the 18V cap rating. The floor $V_("cap,min") = 10.5$V is the point below which the cap can no longer satisfy $V_("A") > V_("B")$ against the 10V bus, so the SMPS can transfer energy in neither direction. Within that window the bank stores energy as $E = 1/2 C V^2$ with $C = 0.5$F (two 0.25F caps in parallel).

#figure(
  image("images/supercap_energy_window.png", width: 88%),
  caption: [Supercapacitor stored energy and usable operating window.],
) <fig:supercap-energy>

In firmware the practical charge ceiling is lowered to 15.7V, kept clear of a region near 16V where the SMPS misbehaves, and a soft taper zeroes the current over the last 0.5V at each edge to avoid slamming into the hard limits. The energy genuinely cycled between 10.5V and 15.7V is approximately 34J of the roughly 49J the full window would hold. A significant practical complication is the bank's approximately 4 ohm equivalent series resistance: immediately after a current step the terminal voltage is dominated by the resistive drop and charge redistribution, so it is an unreliable proxy for state of charge until it settles. This directly shapes the cycle-test settle phases described in Section 4.3, which read the open-circuit voltage only after a deliberate pause. Peak current is clamped to 0.60A, leaving approximately 21% headroom under the 0.76A SMPS hardware limit @cd_dsm_datasheet.

=== Command-Driven CC: Rationale for the Departure

Unlike the grid and export modules, the supercap does not participate in droop. The bus voltage is already regulated by the grid and export droop pair (Section 2.6), so adding the cap as a third droop participant would complicate coordination for no benefit. Instead the cap is a commanded current source and sink: it tracks a signed current command issued by the operator or, in due course, by the economic algorithm. This is the correct abstraction for storage, which the dispatch logic should reach for explicitly to perform temporal arbitrage, charging when energy is cheap and discharging when it is expensive, rather than reacting passively to instantaneous bus voltage.

The control law is therefore an inner current PI only, with no outer voltage loop. The role normally played by an outer loop is filled by a set of soft clamps on the current command: a hard limit at plus or minus 0.60A, a linear taper to zero near each voltage limit, and a bus-health taper that reduces charging demand when the bus sags so the cap does not fight the grid for current. The detailed feedforward and anti-runaway treatment of this inner loop is described in Section 4.2.

=== Simulation

== Testing & Implementation

Three implementation matters specific to the supercap module are reported here: a power-telemetry sign-convention error discovered during efficiency review, the same layered noise treatment described for the PV module in Section 3.2, and the inner-loop feedforward that keeps the synchronous boost stable.

=== Power Telemetry Correction

The original $P_("cap")$ telemetry was computed as $V_("cap") dot I_("L")$, mirroring the PV module's pattern of pairing the Port B voltage with the Port B current. On the PV module this gives the correct panel input power because both factors are physically Port B side measurements. On the supercap module, however, the port assignment is reversed: Port A is the cap and Port B is the bus, so the shunt still measures Port B (bus-side) current while $V_("cap")$ is the Port A voltage. The product $V_("cap") dot I_("bus")$ does not equal the bus-input power $V_("bus") dot I_("bus")$, does not equal the cap-side received power $V_("cap") dot I_("cap")$, and does not equal the rate of cap-side stored energy $C dot V_("cap") dot (d V_("cap")) / (d t)$. It is dimensionally a power but does not correspond to any physical port: the sign is correct (positive while charging) but the magnitude differs from the genuine bus-side transfer power by a factor of $V_("cap") / V_("bus")$, which at $V_("cap") = 15$ V and $V_("bus") = 10$ V is 50% over.

The correction was to compute $P_("cap") = V_("bus") dot I_("L")$ with both factors now Port B side, giving the genuine bus-side power flow. The sign convention is preserved: a positive value means current is flowing into the cap (the bus is delivering, so the value represents the pre-loss bus input), a negative value means current is flowing out of the cap (the bus is receiving, so the magnitude represents the post-loss bus output). This dual interpretation is signalled by the sign, so a single telemetry field carries both meanings without ambiguity. The implication for evaluation is that comparing a charging $P_("cap")$ value directly to a discharging $P_("cap")$ value is comparing pre-loss to post-loss, which is informative but must be interpreted carefully when computing efficiencies.

=== Bench Noise Treatment

The same three-layer noise reduction applied to the PV module is replicated here: INA219 averaging bumped from 8 to 16 samples (CONFIG register 0x1DDF to 0x1E67), four-fold ADC oversampling on $V_("cap")$ and $V_("bus")$ reads, and a software EMA with $alpha = 0.05$ on the V and I traces for the display path. The three-second block average uses one additional reset trigger: the averaging window restarts on changes to $I_("cmd")$, enable state, and cycle-test phase. The cycle-test reset is particularly important because the operating point changes within a test (precharge, charge, discharge) while the user-commanded $I_("cmd")$ stays at zero throughout; without the test-phase term in the reset trigger, the three-second average would smear across phases and become meaningless mid-test.

=== Inner-Loop Feedforward and Bus-Droop Backoff

The inner current PI carries a boost feedforward term equal to the equilibrium duty cycle, $D_("ff") = 1 - V_("bus") / V_("cap")$. At this duty the inductor sees zero net volt-seconds per switching cycle, so its current holds constant and the integrator only has to correct the residual. Without the feedforward the integrator must synthesise the entire steady-state duty, and when the command steps to zero the PI can transiently drive the duty all the way to its floor. In this synchronous boost topology a zero duty clamps the high-side MOSFET on, dumping cap energy back into the bus and crashing the bus rail.

A subtle but critical detail is that the feedforward uses the nominal 10V bus value, not the measured $V_("bus")$. Feeding the measured bus voltage into the feedforward creates a positive-feedback loop with a loop gain near 1.7: a bus sag raises the feedforward duty, which draws more current from the bus, which sags it further. Substituting the constant nominal value breaks the loop, and the integrator absorbs any genuine offset between nominal and actual bus voltage as a small steady-state correction. A complementary bus-health taper scales the charge command down as the bus falls from 9.5V toward 8.5V, so the cap stops competing with the grid module for current during a shared sag; discharging is left untapered because pushing current into a sagging bus helps rather than harms. A hard charge cutoff at 15.7V provides a final backstop above the soft taper.

== Evaluation & Optimisation

The supercap evaluation answers two questions: what is the round-trip energy efficiency $eta_("RT")$, and how does it split into $eta_("charge")$ and $eta_("discharge")$? Both are answered from a single charge-and-discharge cycle, exploiting the cap's known capacitance as an internal calibration reference. The same dataset supports the efficiency-versus-current curve required for Section 11.

=== Energy Balance Method

For a complete cycle from $V_("low")$ up to $V_("high")$ and back to $V_("low")$, three energies are measured. Bus-side input energy is integrated over the charge phase as $E_("in") = integral V_("bus") dot I_("bus") d t$. Bus-side output energy is integrated over the discharge phase as $E_("out") = integral V_("bus") dot |I_("bus")| d t$. Cap-side stored energy at three reference points is computed from the open-circuit cap voltage as $E_("cap") = 1/2 C V_("cap")^2$, captured before charging ($E_("cap,start")$), between the charge and discharge phases ($E_("cap,peak")$) and after discharging ($E_("cap,end")$). The three efficiencies follow:

$ eta_("charge") = (E_("cap,peak") - E_("cap,start")) / E_("in") $
$ eta_("discharge") = E_("out") / (E_("cap,peak") - E_("cap,end")) $
$ eta_("RT") = E_("out") / E_("in") = eta_("charge") dot eta_("discharge") $

The key property of this construction is that no current sensor is required on the cap side: $E_("cap")$ is computed entirely from a voltage measurement and the bank capacitance $C = 0.5$ F (two 0.25 F caps in parallel). This avoids the cascading-efficiency problem flagged in Section 3.3 for the PV characterisation and makes the test fully self-contained inside the supercap firmware.

=== Cycle Test State Machine

The test is implemented as a state machine inside the supercap firmware, triggered from a single dashboard button. Phases run in sequence: precharge (drive $V_("cap")$ down to $V_("low")$ if currently above), settle 1 (zero current for 500 ms, capture $E_("cap,start")$), charge (constant current at the user-specified $I_("charge")$ up to $V_("high")$), settle 2 (capture $E_("cap,peak")$), discharge (constant current at the user-specified $I_("discharge")$ back to $V_("low")$), settle 3 (capture $E_("cap,end")$), done (compute and expose the three efficiencies). Each settle phase averages $V_("cap")$ over only its last 200 ms, skipping the early-settle ESR voltage relaxation transient. Integration of $E_("in")$ and $E_("out")$ runs at the full 1 kHz control tick rate so the displayed efficiencies are not limited by any external sample rate.

Three design decisions in the state machine deserve note. First, the endpoint $V_("low") = 10.5$ V was chosen over a tapered-out $V_("low") = 11.0$ V even though the cap's soft-discharge taper between 11.0 V and 10.5 V (introduced for hard-floor safety) means the discharge current is not held constant at the user-specified value across the final 0.5 V. The energy integral correctly captures the tapered region, and $eta_("discharge")$ legitimately reflects performance averaged across the operational window; the alternative would understate the discharge contribution to round-trip loss. Second, the test bypasses the user-i_cmd path and writes 0 into the command dictionary at start, so when the test ends the cap idles cleanly rather than resuming whatever current command was active before. Third, auto-rearm is implemented: after the done phase the firmware returns to normal command mode, allowing the next test to be triggered with a single button click without intermediate reset.

A 60-second per-phase timeout is enforced as a watchdog; any phase exceeding it transitions to an aborted state. Any trip, disable command, or explicit `test_abort` also transitions to aborted with the partial $E_("in")$ and $E_("out")$ values frozen for download.

=== Data Logging

The host dashboard polls the supercap telemetry endpoint at 20 Hz throughout the test, accumulating every sample into a browser-side JavaScript array. Logged fields per row are timestamp, phase, $V_("cap")$, $V_("bus")$, $I_("L")$, instantaneous bus power, running $E_("in")$, running $E_("out")$, instantaneous cap-side energy ($1/2 C V_("cap")^2$, computed in the browser), and the effective current command. At completion the array is serialised into a CSV blob and downloaded through the browser, landing in the user's default Downloads folder.

The decision to log at 20 Hz from the dashboard rather than at the full 1 kHz from firmware was driven by Pico W RAM constraints. A full 60-second test at 1 kHz with ten fields per sample at 8 bytes each would require approximately 4.8 MB, well beyond the Pico W's 264 kB usable RAM; flash logging would be slow and would wear the chip with each test. The 20 Hz dashboard approach off-loads sample retention to the browser, where the limit is effectively browser memory rather than embedded RAM. The energy integrations themselves remain at 1 kHz internally so the displayed efficiency numbers are not limited by the log rate; the 20 Hz CSV is intended for post-experiment visual inspection and plotting, not for the efficiency calculation itself.

=== Measured Results

The cycle test was run as two sweeps, each repeated three times: a charge and discharge current sweep at 0.1, 0.2 and 0.3A with the bus held at 10V, and a bus voltage sweep at 8.0, 8.5, 9.0, 9.5 and 10.0V with the current fixed at 0.2A. @fig:cap-cycle shows a representative cycle at the 10V, 0.2A operating point. The capacitor voltage ramps from 10.5V to the 15.7V cutoff over a 19-second charge and back over a 17-second discharge, while the bus-side energy integrals accumulate to $E_("in") = 38.2$ J on charge and $E_("out") = 33.7$ J on discharge. The cap-side energy swing $1/2 C (V_("high")^2 - V_("low")^2) approx 34$ J matches the design estimate.

#figure(
  image("images/supercap_cycle_trace.png", width: 100%),
  caption: [Measured supercapacitor charge and discharge cycle at 10V, 0.2A.],
) <fig:cap-cycle>

Round-trip efficiency is reported as $eta_("RT") = E_("out") / E_("in")$, with both energies measured at the bus, so the figure is independent of any cap-side assumption. @fig:cap-eff plots it against current and against bus voltage, showing all three runs per point. The headline result is a round-trip efficiency of approximately 88%, slightly above the conservative 70 to 85% pre-test estimate and stable across the operating range. The dependence on current is weak and slightly negative (89.7% at 0.1A, 88.3% at 0.2A, 88.2% at 0.3A), consistent with conduction loss growing with current. The dependence on bus voltage is weaker still and largely within the run-to-run scatter, with a mild rise toward higher bus voltage (87.3% at 8V to 88.3% at 10V) consistent with the smaller boost ratio, and therefore lower switch stress, when the cap sits closer to the bus.

#figure(
  image("images/supercap_efficiency.png", width: 100%),
  caption: [Measured round-trip efficiency versus current and versus bus voltage.],
) <fig:cap-eff>

#protable(
  columns: (auto, auto, auto),
  align: (left + horizon, center + horizon, center + horizon),
  [*Sweep*], [*Setpoint*], [*Mean $eta_("RT")$, 3 runs*],
  [Current at 10V bus], [0.1A], [89.7%],
  [], [0.2A], [88.3%],
  [], [0.3A], [88.2%],
  [Bus voltage at 0.2A], [8.0V], [87.3%],
  [], [8.5V], [87.7%],
  [], [9.0V], [87.4%],
  [], [9.5V], [88.8%],
  [], [10.0V], [88.3%],
)

The per-phase split into $eta_("charge")$ and $eta_("discharge")$ is deliberately not reported as a headline figure, because the data shows it is unreliable on this bank. The split needs the open-circuit cap energy $1/2 C V^2$ captured at each settle phase, but the supercapacitor's distributed series resistance means the terminal voltage keeps redistributing after the current stops, exactly the effect the brief warns about. The discharge-side split routinely came out above 100%, which is unphysical, because more energy is drawn from the cap on discharge than the post-settle open-circuit voltage implies. Since $eta_("RT") = E_("out") / E_("in")$ is computed entirely from bus-side measurements it is immune to this, and is the figure carried into Section 11. The finding is itself informative: the cap-side voltage is adequate for the state-of-charge display but not for a clean charge versus discharge efficiency split.

The cap cycle test also feeds the future-work automated PV efficiency measurement (Section 3.3): because the bus-side energy delivered into the cap is directly measured, a PV run that charges the cap can be cross-checked against $E_("in")$ without relying on the cap-side split.

=== Extended Current Sweep and Self-Discharge Characterisation

After the firmware command clamp was raised from 0.3A to 0.6A (Section 4.2), the current sweep was extended with three runs each at 0.4A, 0.5A and 0.6A. The cycle-test state machine was then extended with a user-controlled zero-current hold phase between charge and discharge, and a hold-duration sweep at 60, 120, 180, 240 and 300 seconds (three runs each, 0.2A charge / discharge) was run to characterise self-discharge. @fig:cap-hold-eff summarises the three sweeps in a common style.

#figure(
  image("images/supercap_hold_efficiency.png", width: 100%),
  caption: [Round-trip efficiency across the three sweeps. (a) versus charge / discharge current at 10V bus and zero hold, extending the original sweep to 0.6A. (b) versus bus voltage at 0.2A (repeated from Section 4.3, included for direct comparison with the new sweeps). (c) versus hold duration at 0.2A and 10V bus: the cost of parking the cap at high state of charge.],
) <fig:cap-hold-eff>

Panel (a) shows that $eta_("RT")$ sits in a narrow 87 to 90% band across the full 0.1 to 0.6A range, with a mild downward trend (89.7% at 0.1A to 86.9% at 0.5A) consistent with conduction loss scaling with current, and a small recovery to 87.4% at 0.6A inside the run-to-run scatter. Panel (b) is the bus-voltage sweep, with all five points within a 1.5 percentage-point band. Panel (c) is the new finding: $eta_("RT")$ falls from 88.3% with no hold to 64.1% after 300 seconds of hold at peak charge. The largest single step is the first minute (88.3% to 77.5%); subsequent minutes contribute a roughly linear 3 percentage-points-per-minute slope. Because $eta_("RT") = E_("out") / E_("in")$ is measured entirely at the bus this is real energy lost, not a measurement artefact.

#figure(
  image("images/supercap_hold_self_discharge.png", width: 100%),
  caption: [Master self-discharge curve: median $V_("cap")$ across 13 hold runs at 0.2A. Two regimes are visible: a fast dielectric-absorption component over the first 50 seconds (shaded) followed by slow ohmic leakage. All five tested hold durations collapse onto this one curve, so a single two-time-constant model describes the bank.],
) <fig:cap-hold>

@fig:cap-hold underpins panel (c) of the efficiency figure. The median $V_("cap")$ traced across all 0.2A hold runs (irrespective of their commanded hold length) collapses onto a single relaxation curve, confirming that one underlying mechanism dominates: a fast component of approximately 0.5V over the first 50 seconds, attributable to dielectric absorption (charge redistribution into deeper dielectric layers, already flagged in Section 4.1 as the reason the cycle test inserts a settle window before each OCV capture), and a slow component of order 2 to 3mV per second thereafter, attributable to ohmic leakage through the dielectric. That all hold lengths produce the same curve means the relaxation can be fit once and reused for any hold the algorithm chooses.

The implication for the economic dispatch algorithm in Section 11 is direct: the supercap should be charged just-in-time. Even a few minutes of unscheduled hold at peak state of charge materially erodes the round-trip benefit, and slight scheduling slack is cheaper to absorb on the input side (delay charging by a few minutes) than on the output side (charge ahead and let leakage bleed it down).

#pagebreak()


// ----- 5. Import & Export SMPS (~1000 words) -----------------
= Import & Export SMPS

== Design & Simulation

=== Topology Choice

Both grid-facing modules are configured as synchronous buck converters with the BU/BO switch set to BUCK (the shared power stage is @fig:smps-stage), but their port assignments mirror their opposite roles. The import module places the 12V bench PSU on Port A and the bus on Port B, stepping 12V down to the 10V bus and sourcing current into it; it cannot push current back into the PSU, so its current reference is clamped to non-negative values. The export module places the bus on Port A and a dummy resistor bank on Port B, stepping the bus down into the resistor to dissipate surplus energy; its current reference is likewise clamped non-negative. Both satisfy the Port A above Port B rule by construction.

Because the gate driver on these modules inverts, the buck duty is written as `65536 - pwm_out`, the opposite of the PV and supercap boost convention, and the safe state writes a full-scale duty so the MOSFET is held off. Current is sensed by the shared INA219 driver across the 0.10 ohm Port B shunt. The choice of a dummy resistor as the export sink follows the brief's guidance: driving current into a bench PSU causes its current to collapse and its terminal voltage to rise, so a resistor sized to sink the maximum export current without exceeding its voltage limit is used in place of true reverse feed.

The resistance follows from the worst-case exportable surplus. The most the bus could ever need to shed is full photovoltaic harvest plus peak supercapacitor discharge: two panels in parallel supply under 6W, and the supercapacitor at its 17.5V ceiling and 0.76A absolute peak discharge @cd_dsm_datasheet adds about 13W, so the surplus stays under 20W. Because the export converter bucks from the 10V bus, the dissipating voltage cannot exceed the bus, so shedding 20W needs a current of $P / V = 20 / 10 = 2$A and a load of $V / I = 10 / 2 = 5$ ohm. The dummy load is therefore a 5 ohm bank and the inductor-current reference is capped at 2A, the point at which the 10V and 2A limits coincide at the 20W corner, and which sits under the module's 2.8A firmware overcurrent trip.

=== Droop Setpoints: 9.9 V Import and 10.1 V Export

Each module runs a cascaded controller: an outer bus-voltage PI produces a current reference, and an inner current PI servoes the inductor current to it. The two modules differ only in the sign of the voltage error. The import module computes $v_("err") = V_("target") - V_("bus")$, so it sources more current the further the bus falls below its 9.9V setpoint. The export module computes $v_("err") = V_("bus") - V_("target")$, the sign flipped, so it dissipates more the further the bus rises above its 10.1V setpoint. Each reference is clamped to a non-negative cap of 2.0A on both modules (approximately 20W at the bus), the export value set by the worst-case surplus analysis in Section 5.1.1 and the import value by the grid interface rating.

Placing the import setpoint below the export setpoint creates the 0.2V dead-band from 9.9V to 10.1V in which neither module acts, the mechanism analysed at system level in Section 2.6. A setpoint of 0.1V or below, or a disable command, is treated as fully off, which is how a higher-level scheduler hands the bus entirely to one side. During bring-up a deliberately wider band was used, with the import target lowered and the export target raised, to stay tolerant of untuned loops and residual noise before narrowing to the final 9.9V and 10.1V once the loops were stable.

=== Simulation

== Testing & Implementation

Both bus-facing modules received the same three-layer noise reduction as PV and supercap, applied through a single edit to the shared INA219 driver. Because Import and Export use the common `INA219` class in `common.py` rather than an inline driver, raising the CONFIG word from 0x199F (12-bit, single-sample, 532 us conversion) to 0x1E67 (12-bit, 16-sample averaging, 8.51 ms conversion) inside the class constructor benefited both modules with one change. The four-fold ADC oversample on $V_("PSU")$, $V_("bus")$, $V_("dummy")$ and the software EMA on the V and I traces were duplicated into each module's main loop. Three-second block averages of $P_("import")$ and $P_("dissipated")$ were added with reset triggers on $V_("target")$, $I_("max")$ and enable state, matching the per-module pattern used elsewhere.

The Import module's $P_("import") = V_("bus") dot I_("L")$ telemetry was already correctly formulated: both factors are Port B side measurements on the buck topology, so $P_("import")$ is the genuine bus-side delivered power (post-loss). The Export module's $P_("dissipated") = V_("dummy") dot I_("L")$ similarly represents the genuine dummy-resistor dissipation (post-loss at the export converter output). Neither required the formula correction that the supercap module needed in Section 4.2.

=== Anti-Windup and Soft-Start Grace

The outer voltage PI on each module uses clamping anti-windup with a tightly bounded integrator. Left at the default integrator bound the term could wind up tens of thousands of times past the value that already saturates the current reference, taking several seconds to unwind once the bus returned to target and producing a slow limit cycle on the bus, observed as the rail swinging between roughly 8V and 12V at about 1Hz when PV and export ran together without the grid module present. Bounding the integrator to the range that just saturates the output lets it wind up only as far as useful and unwind in time proportional to the error.

A soft-start grace window guards the undervolt trip. When the grid module is the only source during bring-up, the bus begins near 0V, which would latch an undervolt trip on the very first tick before the converter has had any chance to lift the rail. The undervolt trip is therefore masked for 500ms on every transition from inactive to active, that is on enable, on watchdog clear, and on trip reset, while the overvolt and overcurrent trips stay armed throughout. The export module carries the same grace logic for symmetry, although its sink-only reference naturally clamps to zero while the bus is below target.

== Evaluation & Optimisation

The import SMPS efficiency is defined as $eta_("import") = P_("bus,delivered") / P_("PSU,drawn")$. The numerator $P_("bus,delivered")$ is the firmware's $P_("import")$ field. The denominator $P_("PSU,drawn") = V_("PSU") dot I_("PSU")$ requires $I_("PSU")$, which is not measured on the import module because the shunt sits on the Port B (bus) side. Unlike the PV case in Section 3.3, however, $I_("PSU")$ is available with no extra instrumentation and no calibration step: the bench PSU's built-in current readout exposes it directly with manufacturer-stated accuracy. The test procedure reduces to "read the three-second-averaged $P_("import")$ off the dashboard, multiply $V_("PSU")$ by the PSU's current reading, take the ratio".

Section 2.3 established that any watt lost in the import path is a watt of grid energy that does not appear on the bus, directly degrading the economic score. Import efficiency therefore deserves disproportionate evaluation attention, and the sweep is correspondingly fine-grained. Bus voltage is commanded at 9.5, 9.7, 9.9 (the steady-state symmetric-droop setpoint) and 10.0 V, sampling the import operating range. Import current is set at 0.5, 1.0, 1.5 and 2.0 A by manipulating the load applied to the bus. At each grid point the three-second-averaged $P_("import")$ is recorded against the steady-state PSU current reading. The expected outcome is a shallow efficiency maximum at moderate current (approximately 1 to 1.5 A) where conduction losses are not yet quadratic-dominant but switching losses are amortised over enough delivered power. At low currents switching losses dominate the fixed cost; at high currents $I^2 R$ losses in the FETs and inductor windings rise faster than delivered power. The result feeds into Section 11.

The Export module is excluded from the efficiency sweep. Per the architectural rationale in Section 2.3, the project supervisor confirmed that demo-day power measurements are taken at the DC bus bar itself, so all losses on the export path between the bus and the dummy resistor are counted as if they were part of the dissipated load; export's role is to remove excess bus energy when bus voltage exceeds the export droop setpoint, and the module is sized for cost and simplicity, not for peak conversion efficiency. The dummy-resistor dissipation $P_("dissipated")$ is still reported in the telemetry for the system-level energy balance check in Section 11, but the conversion loss between bus and dummy is not separately characterised.

This is an experimental simplification specific to the assessed metric, and is acknowledged as a divergence from real-world deployment economics. In a domestic smart-grid context the export path carries electricity sold back to the utility, and conversion losses between the household bus and the grid connection point reduce the homeowner's revenue per unit of surplus generated. A 90% export SMPS efficiency would mean 10% of every surplus watt is dissipated as heat in the converter rather than monetised through the feed-in tariff. A deployed Export SMPS would therefore face the same efficiency pressure as the Import SMPS does in Section 5.3, because every watt lost is a watt of revenue forgone. The decision to optimise Export for cost rather than efficiency is correct for the assessed brief but would not transfer directly to a fielded system; this is flagged as future work alongside the load-side equivalent in Section 6.3.

#pagebreak()


// ----- 6. LED Load SMPS (~900 words) -------------------------
= LED Load SMPS

== Design & Simulation

=== Topology

The LED load is a triple driver assembly: three independent buck channels (red, yellow, green), each a cut-down SMPS driving a roughly 3W, 1A LED, all controlled by a single Pico W. Buck is the natural choice because an LED forward voltage of around 3V is well below the 10V bus, so the bus is stepped down into each string. The hardware differs from the bidirectional modules in two ways that the firmware must respect. Current is sensed not by an INA219 but by an external SPI ADC of the MCP3208 family, reading three current channels and three voltage channels through one chip select, and the shunt is 0.33 ohm rather than 0.10 ohm, so the inductor current is recovered as $i_("L") = 3 dot V_("shunt")$. Each channel also has a dedicated enable pin that must be driven high on every tick, since the gate driver gates the PWM off whenever its enable is low. The LED forward voltage is reconstructed from the two ADC reads as $v_("LED") = 2 dot v_("v,pin") - v_("i,pin")$, correcting for the sense divider and the shunt drop. One of the three identical driver channels is shown in @fig:led-driver.

#figure(
  image("images/LED_driver.png", width: 92%),
  caption: [LED buck driver power stage, one of three identical channels @clemow_led.],
) <fig:led-driver>

=== Control Mode: CC vs Commanded Power

An LED behaves approximately as a fixed-voltage device, so its power is set by controlling current, which makes a current-controlled inner loop the only sensible drive. The demand from the web server, however, arrives as a power figure, so each channel runs in a commanded-power mode realised through constant current: the demanded power is divided by the measured forward voltage to give a current reference, $i_("ref") = P_("demand") / v_("LED")$, which a per-channel current PI then tracks. The reference is clamped to the channel ratings, 3.0W and 1.05A, and a forward-voltage floor guards the division when a string is dark. When the demanded power for a channel is zero the enable pin is dropped and that channel's PI is reset, preventing the integrator from winding up while the channel is meant to be off.

=== Simulation

== Testing & Implementation

The example driver firmware was reworked to drop its external PID dependency in favour of the same inline PI used across the bidirectional modules, giving one consistent controller idiom throughout the project. The per-channel gains and the duty saturation range differ from the bidirectional modules to suit the 0.33 ohm shunt and the driver's own PWM limits. Safety is per channel: if any channel's current exceeds 1.4 times its rated maximum the firmware latches a trip and records which colour tripped, so a single faulty string is diagnosable from the telemetry rather than presenting as a generic fault.

Two bring-up aids proved useful. A boot-time diagnostic samples every SPI ADC channel several times before the control loop starts, with no PWM commanded, so that a phantom overcurrent caused by a floating ADC input, a wrong port, or a brown-out can be told apart from a genuine LED overcurrent simply by reading the printed values. On shutdown the enables are dropped first, which gates the PWM off at the driver regardless of the commanded duty, before the duties themselves are zeroed, guaranteeing the strings go dark cleanly. The shared 10-second watchdog forces all channels off if commands stop arriving.

== Evaluation & Optimisation

The LED Load SMPS conversion efficiency is not separately characterised. Per the architectural rationale in Section 2.3 and confirmed directly by the project supervisor, the demo-day power measurements occur at the DC bus bar itself, so any loss occurring between the bus and the LED string is counted on the bus side as load consumption rather than as a deduction from the score. The metric therefore treats LED Load SMPS losses as if they were additional LED dissipation, and there is no scoring benefit to driving LED Load SMPS efficiency above whatever the simplest competent design delivers. The module is sized for cost, current capability and PI robustness rather than peak efficiency, on the same logic that excludes the Export SMPS in Section 5.3.

This is an experimental simplification specific to the assessed metric and is acknowledged as a divergence from real-world deployment economics. In a domestic smart-grid context the LED Load SMPS sits on the path between the household DC bus and the actual end-use load (lighting, heating, appliances), so any conversion loss on this path reduces the effective usable power delivered to the homeowner. A 90% LED Load SMPS efficiency would mean that for every kilowatt-hour drawn at the bus, only 0.9 kilowatt-hour reaches the end use, with the remainder dissipated as heat inside the converter. The homeowner would then have to draw more power from the bus to achieve the same usable output, and therefore more from the grid during net-consumption periods. In an active smart-grid economic optimisation this manifests as either decreased revenue when the household is net-exporting (because some local generation goes to converter heating rather than to the grid) or increased import cost when the household is net-consuming (because some imported energy goes to converter heating rather than to the end use), scaled in both cases by one minus the load-side conversion efficiency.

The decision to leave LED Load SMPS efficiency uncharacterised is therefore correct for the assessed brief but represents a known gap relative to a fielded system. Future work, alongside the Export SMPS equivalent flagged in Section 5.3, would include a DMM-instrumented LED Load efficiency sweep across the relevant operating range (LED current and bus voltage), feeding into a refined economic model where the load-side conversion loss enters as a multiplicative penalty on every imported and self-consumed watt.

#pagebreak()


// ----- 7. Sensing & Telemetry (~500 words) -------------------
= Sensing & Telemetry

== INA219 vs SPI ADC Trade-off

The system uses two current-sensing platforms plus a light sensor, each matched to its module. The four bidirectional modules (PV, grid, export, supercap) sense current with an INA219 over I2C across a 0.10 ohm shunt on the Port B positive line. The INA219 suits these modules because their current is genuinely bidirectional, the charge and discharge of the cap and the import and export of the grid all require a signed reading, and because its programmable internal averaging and dedicated 16-bit shunt path give a quiet current signal without consuming Pico ADC channels. The calibration register is deliberately left at zero: rather than trust the chip's internal current scaling, the firmware reads the raw shunt voltage and divides by the known shunt resistance itself, which keeps the current scale traceable to a single resistor value.

The triple LED driver instead inherits an external SPI ADC of the MCP3208 family from the lab reference design, reading three current and three voltage channels across a 0.33 ohm shunt. The LED current only ever flows one way, so the simpler unidirectional ADC is sufficient, and using SPI keeps the three channels independent and the I2C bus free. Finally, irradiance is measured by a light-dependent resistor on a separate ESP32 module, added because all three Pico ADC pins on the bidirectional boards are already committed to on-board signals. Bus and port voltages on every module are read through the Pico's own ADC via a resistive divider, independent of whichever current sensor the module uses. @fig:smps-control shows the controller interface common to the bidirectional modules: the BU/BO switch that selects which port feeds the support-rail regulator, the I2C link to the INA219, the divided Port A and Port B reads on the Pico ADC, and the PWM path through a deadtime generator and gate driver to the two MOSFETs.

#figure(
  image("images/smps_control_diagram.png", width: 100%),
  caption: [Pico controller, sensing and gate-drive interface for the bidirectional SMPS @clemow_control.],
) <fig:smps-control>

== Calibration

Voltage readings are scaled by the resistive divider ratio and the 3.3V ADC reference, of the form $V = (12490 / 2490) dot 3.3 dot ("raw" / 65536)$. Small per-channel trim factors near unity (1.017 and 1.015 on the PV and supercap reads) were applied to null residual divider and reference error measured against a bench multimeter. Current calibration on the bidirectional modules reduces to the single shunt value of 0.10 ohm, since the INA219 calibration register is zeroed and the shunt voltage is converted in firmware; the PGA is set for a plus or minus 320mV shunt range, which across the 0.10 ohm shunt gives a current measurement ceiling of plus or minus 3.2A. The firmware overcurrent trip is placed at 2.8A, just inside this ceiling so that it fires on a valid reading rather than a saturated one, and well under the module's 5A board rating. The LED driver uses its own 2.497V ADC reference and the $i_("L") = 3 dot V_("shunt")$ scaling for the 0.33 ohm shunt.

The irradiance sensor uses a two-point calibration captured from the dashboard: one reading with the lamp off sets the dark point and one at full brightness sets the bright point, and the LDR voltage is then mapped linearly to an irradiance fraction. The two points are persisted in the ESP32's non-volatile storage so the calibration survives a reboot.

== Filtering & Loop-rate Impact

Noise on the per-module power telemetry was severe enough at first bring-up to obscure the operating-point comparisons that Section 3.3, Section 4.3 and Section 5.3 depend on. Typical jitter on $P_("panel")$ was several hundred milliwatts peak-to-peak against a steady-state mean of a few watts, with similar relative magnitudes on the other modules. The fix is a three-layer attenuation applied identically across the PV, supercap, import and export modules; it is documented once here and referenced by each per-module section.

=== Layer 1: INA219 Internal Averaging

The bidirectional template inherits an INA219 CONFIG register of 0x199F, decoded against the datasheet as: BRNG = 0 (16 V bus range), PG = 11 (shunt PGA at ±320 mV full scale), BADC = SADC = 0011 (12-bit, single sample, 532 us conversion), MODE = 111 (continuous shunt and bus). The single-sample 12-bit conversion lets a substantial fraction of switching ripple through unaveraged, particularly on the shunt channel where ripple amplitude is largest. The reprogrammed value 0x1E67 keeps every field identical except BADC and SADC, which are stepped from "single sample" to "16 samples, 8.51 ms". Conversion time rises sixteen-fold but remains an order of magnitude below the slowest downstream consumer (the supercap cycle test's 200 ms OCV averaging window, Section 4.3), so the additional latency is invisible.

The change benefited supercap and PV through identical edits to their inline `ina_init` functions, and import and export through a single edit to the `INA219` class constructor in `common.py`. No code outside the driver had to change, because the I2C reads return the post-averaged value transparently.

=== Layer 2: Pico ADC Oversample

The Pico W's onboard 12-bit ADC walks several LSBs sample-to-sample on the divider-scaled bus and panel voltage channels, dominating the noise on those channels even after the INA219 fix (which only affects the current channel). Each `read_va` and `read_vb` therefore performs four single reads in sequence and right-shifts the accumulated sum by two to obtain the mean:

$ V_("oversampled") = (V[0] + V[1] + V[2] + V[3]) / 4 $

Cost per call is approximately 10 us, well inside the 1 ms control tick budget. The mean reduces the ADC noise contribution by a factor of two on the assumption of independent samples; with the residual driven by correlated low-frequency drift rather than independent white noise, the practical reduction is closer to a factor of 1.6 in observed peak-to-peak jitter. Increasing oversample beyond four shows diminishing returns and starts to eat into the tick budget; four was chosen as the conservative point.

=== Layer 3: Exponential Moving Average

A first-order EMA is applied in software on top of the hardware-averaged readings:

$ V_("filt")[n] = (1 - alpha) dot V_("filt")[n-1] + alpha dot V[n] $

with $alpha = 0.05$ at the 1 kHz sample rate, equivalent to a time constant $tau approx 20$ ms and a corner frequency around 8 Hz. The filtered signals drive the dashboard display, the three-second block averages, the P&O power comparison (Section 3.2) and the cycle-test energy integrators (Section 4.3). The choice of $alpha = 0.05$ is bounded by two constraints. Too small (longer $tau$) and the filter introduces phase lag that would slow the displayed transient on dashboard reads; too large (shorter $tau$) and the filter passes switching-ripple aliasing through. 20 ms is approximately 60 ms to settle to 95% of a step input, which fits inside the 150 ms second-half averaging window of the P&O dwell and inside the 200 ms tail of the cycle-test settle phases. @fig:ema-response shows the resulting response: a corner near 8Hz that rejects the aliased switching ripple, with a step settling inside 60ms so the displayed transient is barely delayed.

#figure(
  image("images/ema_filter_response.png", width: 100%),
  caption: [Telemetry EMA magnitude and step response at alpha = 0.05.],
) <fig:ema-response>

The filter is initialised to the first sample at boot via a "kick start" branch, avoiding a 60 ms ramp-from-zero on the displayed values at startup.

A critical design decision is that the inner PI loops and the safety guards continue to consume the raw single-sample readings, not the filtered values. Two reasons. First, introducing a 20 ms phase lag into a current PI tuned against unfiltered inputs would shift its stability margin and require retuning. Second, the trip thresholds in each module (panel undervolt, bus overvolt, overcurrent) were designed for instantaneous response; a filtered safety guard would react with a 20 ms delay, which is fast enough to be invisible to a human operator but slow enough to allow more energy to flow into a fault before tripping. Keeping the filter strictly on the display and characterisation paths preserves both control-loop behaviour and trip response while still giving the operator clean numbers to read.

=== Three-Second Block Average

Each module computes a true block average of its bus-side power over a three-second window in firmware:

$ P_("avg3s") = (1 / N) sum_(i=1)^(N) P[i] $

with $N = 3000$ at 1 kHz. The window restarts on changes to the module's commanded operating point (MPPT mode for PV, $I_("cmd")$ for supercap, $V_("target")$ and $I_("max")$ for import), so each completed average reflects a single operating point. Float-rounding the operating-point tuple before comparison (`round(value, 3)` or `round(value, 2)` depending on field) avoids spurious resets from JSON-parser dust. The completed average is what the operator reads from the dashboard during the side-by-side comparisons in Section 3.3 and Section 5.3.

The three-second window is short enough that operators wait only briefly between commanded changes, and long enough that filter noise and switching ripple average out to a stable number. Inside the supercap cycle test the same three-second average sits on top of the cycle phase changes (which are themselves on the timescale of seconds to tens of seconds), so it provides a useful real-time sanity check that the cycle's commanded current has actually settled.

== Evaluation

#pagebreak()


// ----- 8. User Interface (~1000 words) -----------------------
= User Interface

The user interface satisfies the brief's requirement for a display of current and historic information about energy flows and stores, and extends it with full operator control of every module. The whole stack was written in-house as three cooperating tiers.

== Architecture

The lowest tier is a hand-rolled HTTP server embedded in every module's firmware. It exposes a telemetry endpoint and a command endpoint and runs on the Pico's second core, deliberately isolated from the 1kHz control loop on the first core, so that no network activity can ever stall or jitter the safety-critical control timing. Telemetry is published as a JSON snapshot and commands are accepted as a JSON object merged into the module's command dictionary.

The middle tier is a Python backend built on FastAPI with a SQLite store. A poller fetches the telemetry endpoint of each module on a roughly one-second cadence and the external grid signals (demand, irradiance, buy and sell price, and the deferrable-load list) once per tick, writing both into time-stamped tables. Grid snapshots are de-duplicated by day and tick so the history is clean. The backend then serves this data to the frontend through a small set of read endpoints for the latest grid state, recent snapshots, and per-module telemetry.

The top tier is a React single-page application built with Vite. It polls the backend on a short interval, keeps a client-side rolling history of recent samples per module, and renders three operator views.

== Operator Views

The default My Energy view is a consumer-facing dashboard styled after a domestic energy provider. It presents the live grid state as demand and irradiance bar charts, a module status grid that flags each module as online, stale, tripped, on watchdog, or disabled, the current buy and sell prices, and the deferrable-load list rendered as progress bars showing each job's window and time remaining. The SMPS Overview view plots per-module telemetry histories (panel, bus, capacitor and load voltages, currents and powers) as line charts drawn from the stored snapshots. The SMPS Modules view is the engineering control surface: one card per module showing its live statistics, a mini history chart, a status pill, and a control panel tailored to that module's role.

The control panels expose exactly the commands each module understands. The PV card switches between fixed, web-lookup and Perturb-and-Observe MPPT and sets a manual maximum-power voltage. The grid and export cards set the bus target and current cap and toggle the module off by setting a zero target. The supercap card offers a signed current slider with charge, discharge and stop shortcuts, and triggers the self-contained efficiency cycle test. The LED card sets per-channel power demands, and the irradiance sensor card runs the two-point calibration. Every card carries enable, disable and reset-trip controls.

== Control and Telemetry Paths

A deliberate design choice is that the control path and the telemetry path are independent. Telemetry flows up through the backend and database, but commands are sent straight from the browser to each module's own command endpoint, using the permissive cross-origin policy the firmware sets for this purpose. The two paths therefore share no single point of failure: if the backend or database is down the operator can still command modules directly, and if a module's command endpoint is unreachable the rest of the system keeps reporting. Combined with the firmware watchdog, which forces a module to safe defaults if commands stop arriving, this keeps the interface advisory rather than safety-critical, consistent with the coordination philosophy of Section 2.6.

== On-Module Fallback Dashboard

As a final redundancy a complete single-file dashboard is bundled into the firmware filesystem and served by the module's own HTTP server at its root path. This gives a usable monitoring and control surface with no backend, no database and no Node toolchain running at all, which is valuable during bench bring-up and as a fallback if the main stack is unavailable on demo day.

#pagebreak()


// ----- 9. Algorithm Software (~1000 words) -------------------
= Algorithm Software

This section covers the system-level coordinator that turns the acquired price, demand and irradiance signals into dispatch decisions across the modules. The per-module control loops of Sections 3 to 6 and the data-acquisition pipeline of Section 8 are complete; the economic decision policy that sits on top of them is the project's principal remaining work ahead of demo day, so the subsections below state the problem the coordinator must solve and the fault model it inherits, and leave the decision policy and its evaluation to be reported once implemented.

== Master Loop & Timing Budget

== Economic Model

The objective is set directly by the brief: minimise the net cost of grid energy over a daily cycle while always meeting demand. With import and export power metered at the bus, the cost accumulated over the cycle is

$ C = sum_t (P_("import")(t) dot p_("buy")(t) - P_("export")(t) dot p_("sell")(t)) dot Delta t $

where $p_("buy")$ and $p_("sell")$ are the per-tick prices read from the web service. The coordinator minimises $C$ subject to a power balance at the bus on every tick,

$ P_("PV") + P_("import") + P_("cap,dis") = P_("demand") + P_("export") + P_("cap,chg") + P_("loss") $

and to several constraints: the instantaneous demand must be met at all times; each deferrable job must receive its specified energy somewhere inside its allowed time window; the supercapacitor must stay within its energy window and current limit (Section 4); and import and export must stay within their current caps (Section 5).

The levers available to the coordinator are therefore which deferrable loads to run when, when to charge or discharge the supercapacitor, and when to import or export. The economically interesting behaviour is temporal arbitrage: deferring flexible loads into ticks with cheap energy or surplus PV, charging the cap when price is low or PV would otherwise be curtailed, and discharging it (or exporting) when price is high. The brief sets the bar explicitly: the policy must beat a naive baseline that always minimises instantaneous import or export and serves every demand immediately. That baseline is the natural comparison point for the evaluation once the policy is implemented.

== Decision Policy / State Machine

== System-Level Fault Handling

Because the coordinator is advisory rather than safety-critical (Section 2.6), system-level robustness currently rests on distributed mechanisms already present in firmware rather than on a central fault handler. Each module carries a watchdog that forces it to safe defaults if commands stop arriving, so a stalled coordinator or dropped link degrades the economic optimisation without threatening the bus, which continues to regulate on local droop. Latching trips with dashboard reset, the soft-start grace window, and the per-module current and voltage clamps described in Sections 3 to 6 contain faults locally. A centralised fault response that reacts to module dropout or trips at the dispatch level is left as future work alongside the decision policy.

== Evaluation

#pagebreak()


// ----- 10. Mechanical Design & Project Polish (~400 words) ---
= Mechanical Design & Project Polish

== 3D-Modelled SMPS Enclosure

The four bidirectional SMPS boards and the triple LED driver were housed in a 3D-printed chassis rather than left as loose boards on the bench. The enclosure fixes each board in a defined position with spacing for airflow between the converters, protects the exposed power electronics from accidental shorts during handling, and gives the assembly a single rigid form that can be moved and demonstrated without disturbing the wiring. Positioning the boards deliberately also keeps each module's sensing and PWM wiring short and consistent, which matters for the noise behaviour discussed in Section 7.

== Cable Management and Connector Choice

Power interconnects use 4mm banana leads into the shared DC busbar, the connector standard of the lab kit, so any module can be attached to or removed from the bus without tools and without disturbing the others, mirroring at the physical layer the modular join-and-leave property that the droop coordination provides electrically. Routing the bus connections through a single busbar keeps the high-current paths short and identifiable and gives an unambiguous single point at which demo-day bus power is measured.

#pagebreak()


// ----- 11. System-Level Testing & Evaluation (~1000 words) ---
= System-Level Testing & Evaluation

== Test Scenarios

System-level evaluation comprises three categories of test: per-module SMPS efficiency characterisations (the headline numbers reported here), bus-stability scenarios that exercise the multi-module droop interactions defined in Section 2, and full demo-day economic-dispatch dry runs against scripted price-and-irradiance profiles. The first category is described in this section; the second and third are introduced in Section 9.

=== Per-Module Efficiency Sweeps

Each SMPS module is characterised across a small grid of operating points, with the test method tailored to the instrumentation available on that module's port assignment. The three methods are summarised below; full details for each are in the relevant per-module evaluation subsection.

PV SMPS (Section 3.3): manual measurement using a DMM placed in series with the PV-to-bus wire. The pre-loss panel power $P_("panel,in")$ is available directly from the firmware (both factors are Port B); the post-loss bus power $P_("bus,out")$ requires the external DMM because Port A is uninstrumented. The bus-voltage axis is swept across seven points from 7.1 to 10.2 V in 0.5 V steps, deliberately wider than the import/export dead-band to capture the full duty-cycle response; this axis is complete at 100% irradiance and gives a mean conversion efficiency of 97.3% across the operating range (Section 3.3.3). The 25%, 50% and 75% lab-dimmer settings are scheduled for the next test session and will close out the irradiance axis.

Supercap SMPS (Section 4.3): fully automated cycle test triggered from the host dashboard. The test integrates bus-side $E_("in")$ and $E_("out")$ at the 1 kHz tick and reports the round-trip efficiency $eta_("RT") = E_("out") / E_("in")$ from a single charge and discharge cycle. The sweep covers charge and discharge current at three levels (0.1, 0.2, 0.3 A) at a 10V bus, and bus voltage at five levels (8.0 to 10.0 V) at 0.2 A. The measured round-trip efficiency is approximately 88%.

Import SMPS (Section 5.3): manual measurement using the bench PSU's built-in current readout for the pre-loss $P_("PSU,drawn")$ side; the post-loss $P_("bus,delivered")$ is available from the firmware. Sweep is bus voltage at four points and import current at four points.

Export SMPS is not characterised for efficiency because its losses occur between the bus and the dummy resistor and are not counted by the demo-day metric (Section 2.3).

== Performance Metrics

The headline metrics extracted from the efficiency sweeps are tabulated below. Each entry is a ratio of post-loss output power to pre-loss input power, averaged over the relevant operating window. For the supercap, the round-trip efficiency is reported per operating point, the per-phase charge and discharge split being confounded by the cap's charge redistribution (Section 4.3). For PV and import, a single number is reported per operating point. All numbers are accompanied by their operating point (bus voltage, current, irradiance) and by the underlying $P_("in")$ and $P_("out")$ raw readings so the ratios can be audited.

In addition to the SMPS efficiency table, two derived system-level metrics are reported. The first is the steady-state bus voltage error against the 10 V nominal under each of the Section 11 test scenarios, measured against the ±0.1 V droop budget defined in Section 2.3. The second is the energy balance closure across the bus for full-cycle scenarios:

$ E_("PV,bus") + E_("import,bus") = E_("export,bus") + E_("LED,bus") + E_("supercap,bus") + E_("losses,bus") $

The unmodelled $E_("losses,bus")$ residual captures bus-wire $I^2 R$ and any uncharacterised dissipation, and is expected to be small (a few percent at most) if the per-module post-loss measurements are consistent. An anomalously large residual on a closure check is treated as a regression signal for the per-module efficiency numbers.

== Requirements Verification Matrix

Each of the brief's six requirements is mapped below to the subsystem that realises it, the test that verifies it, and its current status. Requirement 5, the economic dispatch algorithm, is the principal item still in progress (Section 9); the remainder are implemented and verified by the tests described in the cited sections.

#protable(
  columns: (auto, 2fr, 1.4fr, 1.5fr, 1.2fr),
  align: (center + horizon, left + horizon, left + horizon, left + horizon, left + horizon),
  [*Req*], [*Requirement*], [*Realised by*], [*Verification*], [*Status*],
  [1], [Supply domestic LEDs per web demand], [LED Load SMPS (Section 6)], [CC power-following; demand poll], [Implemented],
  [2], [Extract PV energy with MPPT], [PV SMPS (Section 3)], [MPPT mode comparison; efficiency sweep], [Implemented],
  [3], [Store excess in supercap, no batteries], [Supercap SMPS (Section 4)], [Cycle test; round-trip efficiency], [Implemented],
  [4], [Import and export to grid, metered], [Import/Export SMPS (Section 5)], [Import efficiency sweep; bus dead-band], [Metering done; costing via Section 9],
  [5], [Minimise cost; schedule storage and deferrables; beat naive], [Algorithm (Section 9)], [Dry run versus naive baseline], [In progress],
  [6], [UI for current and historic energy data], [User Interface (Section 8)], [Live dashboard; telemetry plots], [Implemented],
)

#pagebreak()


// ----- 12. Conclusion (~150 words) ---------------------------
= Conclusion

The project delivered a five-module DC microgrid that regulates a shared 10V bus across PV generation, supercapacitor storage, a bidirectional grid interface and a programmable LED load. The two grid-facing converters coordinate the bus through symmetric droop with a 0.2V dead-band, holding the bus stiff without a central coordinator and degrading gracefully under communication loss. The PV module runs selectable lookup-table and Perturb-and-Observe MPPT; the supercapacitor is a command-driven store with a self-contained cycle test that returns round-trip efficiency from a single voltage measurement; the LED load follows commanded power through constant current. A three-layer telemetry filter chain made per-module power measurements quiet enough to characterise, and a self-coded React and FastAPI interface provides both monitoring and control with independent telemetry and command paths. The principal remaining work before demo day on 18 June 2026 is the economic dispatch algorithm that turns the acquired price and demand signals into cost-minimising decisions.

// ============================================================
//  References
// ============================================================
#pagebreak()
#bibliography("references.bib", title: "References", style: "ieee")
