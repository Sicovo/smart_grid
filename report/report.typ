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
    Dzuldiniy (CID) \
    Ooi Chun Wen (CID) \
    Ooi Wei Zen (CID) \
    Tan Fangnan (CID) \
    Tan Hong Zhe (02562503) \
    Tong Yong Zhi (CID) \
    Wu Yida (CID)
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

Coordinating a seven-member hardware team across a five-month delivery window required tooling that off-the-shelf platforms could not provide as a single integrated system. Rather than stitching together Notion, Trello, Microsoft Teams and ChatGPT, each of which solves only a fragment of the problem and none of which share state, a bespoke AI-powered Project Management System (PMS) was self-coded for the project. Every layer of the frontend, backend, AI pipeline and database schema was purpose-built around the rhythm of the team and the constraints of the brief.

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

#table(
  columns: (auto, auto, auto, auto, auto),
  align: (left, left, left, left, left),
  stroke: 0.5pt,
  [*Module*], [*External component*], [*Topology*], [*Control*], [*Role on the bus*],
  [Import SMPS], [12V grid PSU], [Buck], [CV, droop at 9.9V], [Sources current when bus < 9.9V],
  [Export SMPS], [Sink resistor], [Buck], [CV, droop at 10.1V], [Sinks current when bus > 10.1V],
  [PV SMPS], [6.23V PV panel], [Boost], [MPPT], [Harvests panel power into bus],
  [Supercap SMPS], [10.5 to 17.5V supercap], [Bidirectional buck/boost], [CC, commanded], [Stores or releases on command],
  [LED Load SMPS], [3V LED module], [Buck (internal)], [CC], [Drives the LED load],
)

The two grid-facing modules share a common topology (synchronous buck) and a common control law (droop), differing only in their droop setpoints. This is what creates the dead-band around the nominal bus voltage discussed in §2.5. The Supercapacitor SMPS departs from droop entirely and runs as a commanded current source, which allows the economic algorithm in §9 to use storage as temporal arbitrage rather than as a passive load-sharing element. The LED Load SMPS is internally managed and exposes only its bus-side power draw to the rest of the system.

== Overall Microgrid Topology

The complete system is shown in @fig:arch-block. External components sit at the top of the diagram, each connected through their respective SMPS module to the shared 10V DC bus. Every SMPS is driven by a dedicated Pico W microcontroller running its local control loop. A React backend server polls an Azure-hosted web service every 5 seconds for the current demand, price and irradiance signals, computes the dispatch decision documented in §9, and pushes setpoint commands to the modules through the ESP32 coordinator. The operator-facing dashboard renders telemetry from the same backend.

#figure(
  image("images/arch_block.png", width: 100%),
  caption: [Smart Grid system architecture and power flow.],
) <fig:arch-block>

Three properties of this topology are referenced repeatedly in later sections. First, every SMPS module is fully autonomous in its bus-regulation role: it requires only its local V_bus measurement to act, and the backend provides only setpoint commands and economic context. Second, all demo-day power measurements occur at the bus, never at the individual SMPS terminals. Third, the supercapacitor is the only element capable of storing energy across timescales longer than the bus capacitance, which makes its commanded behaviour central to the economic optimisation in §9.

== Bus Voltage Choice: 10 V Nominal, ±0.1 V Droop Band

The 10V nominal bus value is the smallest round-number voltage that simultaneously sits below the supercapacitor charge window, sits above the PV panel open-circuit voltage of approximately 8.5V, and leaves enough headroom for a buck-derived import from a 12V supply (justified in §2.4). Setting the bus higher would increase switching stress on every buck module without improving any system property. Setting it lower would force the supercapacitor window to a less convenient range and increase the PV boost ratio. Ten volts is also a natural target for hobbyist instrumentation.

Each droop-controlled module follows a local linear control law of the form

$ I_("module") = (V_("set") - V_("bus")) / R_("droop") $

with sign and saturation chosen by the module's role. The droop resistance $R_("droop")$ is sized so that the module current saturates at its rated maximum exactly at the edge of the ±0.1V band. This bounds the steady-state bus error to ±0.1V at full load, which is ±1% of nominal and tight enough to be a stiff bus for all downstream loads.

A critical consequence of taking demo-day measurements on the bus itself is that conversion losses on different paths are weighted asymmetrically in the score. For the LED Load SMPS and the Export SMPS, the losses lie between the bus and the destination, so the bus delivers $P_("destination") + P_("losses")$ and the metric counts the sum as either load or export. SMPS efficiency on those two paths therefore does not affect the score, and the modules can be sized for cost or simplicity rather than peak efficiency. For the Import SMPS the losses lie between the 12V supply and the bus measurement point, so the bus receives only $P_("grid") - P_("losses")$. Every watt lost in the import path is grid energy that does not appear at the bus, directly degrading the economic score. Import SMPS efficiency therefore receives disproportionate attention in §3 and §11.

== PSU Voltage Rationale: 12 V

The choice of 12V for the primary supply is driven by efficiency. For a synchronous buck converter, the steady-state conduction loss summed across both switches is

$ P_("cond") = D dot I_("rms")^2 dot R_("ds,on,HS") + (1 - D) dot I_("rms")^2 dot R_("ds,on,LS") $

When the high-side and low-side MOSFETs are matched, $R_("ds,on,HS") = R_("ds,on,LS") = R_("ds,on")$, and the duty cycle terms collapse:

$ P_("cond") = I_("rms")^2 dot R_("ds,on") $

independent of D and therefore independent of $V_("in")$. Switching loss, in contrast, does not collapse:

$ P_("sw") approx 1/2 dot V_("in") dot I_("load") dot (t_r + t_f) dot f_("sw") + 1/2 dot C_("oss") dot V_("in")^2 dot f_("sw") $

Every term scales with $V_("in")$ or $V_("in")^2$. Inductor ripple also shrinks as $V_("in")$ approaches $V_("bus")$:

$ Delta I_L = (V_("in") - V_("bus")) dot D dot T / L $

which reduces inductor RMS current and copper loss as a second-order benefit. The net result is that import SMPS efficiency rises monotonically as $V_("in")$ is reduced toward $V_("bus")$.

The floor on $V_("in")$ is set by dropout. The buck controller must maintain $V_("in") gt.eq V_("bus") + V_("dropout")$ under worst-case bus droop transients, where $V_("dropout")$ is typically 0.5V to 2V depending on controller architecture and inductor sizing. With $V_("bus") = 10$V and a generous 2V dropout budget, the practical minimum is $V_("in") = 12$V. Twelve volts also coincides with the standard lab bench-supply rail, simplifying procurement and connectorisation.

A confirmation experiment is flagged in §12 (Future Work): sweep $V_("in")$ from 11V to 14V at fixed $V_("bus") = 10$V and measure import SMPS efficiency. The expectation, given the analysis above, is a shallow monotonic rise as $V_("in")$ falls toward 11V, ending in a steep efficiency cliff once dropout kicks in.

== Coordination Scheme: Symmetric Droop vs Mutex Arbitration

Two architectures were considered for coordinating the bus. Mutex arbitration assigns control to exactly one module at a time, with a central coordinator switching modes (PV-controlled, grid-controlled, supercap-controlled) as conditions change. Symmetric droop instead allows every module to act simultaneously, each modulating its own current from a local V_bus measurement relative to its setpoint.

Mutex arbitration produces tighter bus regulation in steady state because exactly one feedback loop is active at a time. However, it places the inter-module communication channel inside the safety-critical bus-regulation loop: if comms drop or the coordinator stalls, every module loses its reference and the bus collapses. Mode transitions also generate voltage transients as the active controller hands over.

Symmetric droop avoids both failure modes. Each module's control loop is local and continuous, requiring only its own bus measurement, so a comms failure degrades the economic optimisation in §9 but does not threaten bus stability. The droop curves blend rather than switch, eliminating handover transients, and modules can join or leave the bus arbitrarily without reconfiguring a coordinator. The cost is a small steady-state V_bus error, bounded to ±0.1V by design as derived in §2.3.

Symmetry is enforced by mirroring the import and export setpoints about the 10V nominal:

$ V_("set,import") = 9.9 "V" quad quad V_("set,export") = 10.1 "V" $

This creates a dead-band $V_("bus") in [9.9, 10.1]$ V in which neither grid-facing module acts. Inside the dead-band the bus is held by the PV harvester and the supercapacitor, which is precisely the configuration the algorithm in §9 seeks to maximise (no grid interaction means no cost incurred). Outside the dead-band the system gracefully falls back to grid import or export with no explicit mode-change logic. The droop curves for all five modules are shown in @fig:droop-curves.

#figure(
  image("images/droop_curves.png", width: 85%),
  caption: [Droop curves: module current versus bus voltage.],
) <fig:droop-curves>

Choosing droop over mutex maps directly onto the single-point-of-failure mitigation theme introduced in §1.2. The communication layer becomes advisory, not safety-critical, and is described next.

== Communication Protocol

The communication protocol is provisional and described here at the architectural level only. A central ESP32 module hosts a WiFi access point joined by every Pico W. Setpoint commands, telemetry and economic context flow over this link in JSON-framed messages. The React backend sits one layer above the ESP32, polling the Azure-hosted web service every 5 seconds for current demand, price and irradiance signals, computing the dispatch decision (§9), and pushing setpoint updates back down to the modules. The 5-second cadence balances Azure rate-limit considerations against the natural timescale of the demand-and-price signal. The dashboard frontend renders telemetry from the same backend without participating in control.

Crucially, the protocol layer sits outside the safety-critical bus-regulation loop. Comms loss leaves every module operating against its last commanded setpoint with its local droop or CC law intact, so the bus continues to regulate. Final framing details (transport, framing, retry policy, error handling) are deferred until module integration testing in §11.

#pagebreak()


// ----- 3. PV SMPS (~1000 words) ------------------------------
= PV SMPS

== Design & Simulation

=== Topology Selection

=== MPPT Strategy: Lookup Table vs P&O

=== Component Sizing

=== LTspice / Python Simulation

== Testing & Implementation

== Evaluation & Optimisation

#pagebreak()


// ----- 4. Supercapacitor SMPS (~1000 words) ------------------
= Supercapacitor SMPS

== Design & Simulation

=== Boost Topology and Boot-with-Empty-Cap Rationale

=== Operating Window 10.5 to 17.5 V

=== Command-Driven CC: Rationale for the Departure

=== Simulation

== Testing & Implementation

== Evaluation & Optimisation

#pagebreak()


// ----- 5. Import & Export SMPS (~1000 words) -----------------
= Import & Export SMPS

== Design & Simulation

=== Topology Choice

=== Droop Setpoints: 9.9 V Import and 10.1 V Export

=== Component Sizing

=== Simulation

== Testing & Implementation

== Evaluation & Optimisation

#pagebreak()


// ----- 6. LED Load SMPS (~900 words) -------------------------
= LED Load SMPS

== Design & Simulation

=== Topology

=== Control Mode: CC vs Commanded Power

=== Component Sizing

=== Simulation

== Testing & Implementation

== Evaluation & Optimisation

#pagebreak()


// ----- 7. Sensing & Telemetry (~500 words) -------------------
= Sensing & Telemetry

== INA219 vs SPI ADC Trade-off

== Calibration

== Filtering & Loop-rate Impact

== Evaluation

#pagebreak()


// ----- 8. User Interface (~1000 words) -----------------------
= User Interface

#pagebreak()


// ----- 9. Algorithm Software (~1000 words) -------------------
= Algorithm Software

== Master Loop & Timing Budget

== Economic Model

== Decision Policy / State Machine

== System-Level Fault Handling

== Evaluation

#pagebreak()


// ----- 10. Mechanical Design & Project Polish (~400 words) ---
= Mechanical Design & Project Polish

== 3D-Modelled SMPS Enclosure

== Cable Management and Connector Choice

#pagebreak()


// ----- 11. System-Level Testing & Evaluation (~1000 words) ---
= System-Level Testing & Evaluation

== Test Scenarios

== Performance Metrics

== Requirements Verification Matrix

#pagebreak()


// ----- 12. Conclusion (~150 words) ---------------------------
= Conclusion


// ============================================================
//  References
// ============================================================
#pagebreak()
#bibliography("references.bib", title: "References", style: "ieee")
