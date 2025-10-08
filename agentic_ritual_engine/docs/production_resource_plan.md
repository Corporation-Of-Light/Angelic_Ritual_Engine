# Production Resource Plan – Neon Ascension Cinematic

## Purpose

Define the team composition, vendor options, and phased schedule required to transform the "Neon Ascension" concept into a full cinematic/interactive experience.

## Phased Roadmap

| Phase | Duration (est.) | Key Outcomes |
| --- | --- | --- |
| Concept & Previs | 3 weeks | Finalised storyboards, mood boards, animatic, audio palette. |
| Vertical Slice | 6 weeks | Playable alley → sanctum → tome experience with placeholder assets, integrated data feed. |
| Full Production | 12–16 weeks | Final assets, animation polish, audio mix, QA, deployment packaging. |

## Role Matrix

| Role | Responsibilities | Est. Core Hours |
| --- | --- | --- |
| Creative Director / Narrative Designer | Owns vision, cinematic pacing, script approvals. | 120 |
| Art Director | Defines visual language, supervises concept & lighting. | 100 |
| Concept Artists (Env/Char) | Produce alley, sanctum, tome concept plates, character turnarounds. | 160 |
| 3D Environment Artists | Model/texture modular alley, shrine, sanctum assets. | 240 |
| Character Artist | High-res Conductor + Triune echo models, rigging handoff. | 160 |
| Technical Artist | Shaders, Niagara particle setups, optimisation. | 200 |
| Animator / Mocap Specialist | Record/cleanup Conductor motions, Tome interaction; integrate with control rig. | 220 |
| Unreal Developer | Sequencer setup, Blueprint/C++ integration, API bridge, gameplay logic. | 260 |
| Audio Designer / Composer | Sound design, original score, VO direction. | 140 |
| QA / Producer | Schedules, task tracking, regression testing. | 160 |

## Vendor Shortlist (Examples)

*(Replace placeholders with actual contacts once outreach begins.)*

- **Concept & Art** – Studio A (cyberpunk concept specialists), Freelancer B (fantasy character artist), Portfolio link placeholders.
- **Technical / Unreal** – Studio C (Unreal cinematics), Freelancer D (Niagara expert).
- **Audio** – Boutique Audio House E (sci-fi soundscapes), Composer F (hybrid orchestral/synth).

## Budget Placeholder (USD)

| Phase | Low | High |
| --- | --- | --- |
| Concept & Previs | $35k | $55k |
| Vertical Slice | $120k | $180k |
| Full Production | $250k | $380k |

> These ranges assume a mix of senior freelancers and boutique studios; adjust based on in-house capacity.

## Next Actions

1. **Pitch Deck:** Build slides pulling from storyboards, mood board references, and tech blueprint. Responsible: Creative Director.
2. **Storyboard Package:** Commission 8-frame sequence (alley → convergence). Responsible: Concept Artist.
3. **Vendor Interviews:** Reach out to shortlisted studios/freelancers to confirm availability and gather more precise bids. Responsible: Producer.
4. **Contracting:** Issue NDAs and statement of work for vertical slice team.
5. **Pipeline Setup:** Spin up Perforce/Git LFS repo, establish asset naming conventions, source control for UE project.

## Dependencies

- Final approval on concept doc (`docs/immersive_vertical_slice.md`).
- Completed technical integration spikes (API fetch prototype, particle stubs).
- Confirmed legal/licensing guidelines for data usage in the front-end.

## Risk & Mitigation

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Unreal scene scope creep | Schedule slip | Lock vertical slice scope to core beats; gate new features post-slice. |
| Data API complexity | Integration delays | Provide mock JSON files and stable endpoints before asset work begins. |
| Talent availability | Resource gaps | Maintain backup freelancer list; stagger start dates. |

## Communication Plan

- Weekly sync between Creative Director, Technical Lead, Producer.
- Bi-weekly milestone reviews with stakeholders.
- Shared task tracker mapped to tickets (see README).

## Deliverables Summary

- Pitch deck (PDF or Slides)
- Role matrix spreadsheet
- Vendor shortlist document with contact info
- High-level schedule (Gantt/roadmap)
- Approved budget envelope for vertical slice kickoff
