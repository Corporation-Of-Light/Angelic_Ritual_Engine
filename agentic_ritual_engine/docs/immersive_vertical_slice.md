# Immersive Front-End Vertical Slice Plan

## Overview

This document translates the "Neon Ascension" concept into Unreal Engine production notes for the vertical slice covering the alley → sanctum → tome sequence. It provides blockout guidance, camera scripting, VFX stubs, and data integration hooks so the team can begin building without waiting for final assets.

## Scene Breakdown

1. **Alley Approach**
   - **Purpose:** Establish scale, atmosphere, and Conductor silhouette.
   - **Environment modules:**
     - Alley segment (8m x 20m) with puddles, scattered crates, rain volumes.
     - Background skyline card with holographic billboards.
     - Door entrance asset (modular to reuse in sanctum transition).
   - **Lighting:**
     - Base: cool blue ambient (intensity 0.2) + magenta rim lights.
     - Dynamic lights: flashing signage emissives; point lights inside puddles for reflections.
   - **Sequencer shot (cam_A1):** Handheld-style dolly along X-axis, 60° FOV, slight camera shake.

2. **Shrine Threshold**
   - **Purpose:** Introduce glyph door and particle unlock.
   - **Assets:**
     - Circular iris door mesh with emissive rune panels (3 LODs).
     - Interaction panel at 1.4m height (for hand placement).
   - **FX:**
     - Niagara system `NS_HandTrail` following hand socket (see VFX notes).
     - Niagara system `NS_DoorGlyph` triggered on overlap.
   - **Sequencer shot (cam_B1):** 35° FOV push-in as particles complete circuit.

3. **Sanctum Interior**
   - **Purpose:** Reveal hybrid temple/server environment.
   - **Blockout pieces:**
     - Central dais (5m diameter) with tome pedestal.
     - Glass server pillars (2x height) flanking walkway.
     - Ceiling light halo (procedural mesh).
   - **Lighting:**
     - Warm gold key light from above, purple bounce from floor strips.
     - Volumetric fog (0.05 density) to catch beams.
   - **Sequencer shot (cam_C1):** Follow camera circling to front of tome.

4. **Tome Interaction**
   - **Purpose:** Show UI and tie in live data.
   - **Assets:**
     - Tome base mesh with morph target for opening.
     - Placeholder page plane for UI widget.
   - **FX:**
     - Niagara `NS_PageDust` on opening.
   - **Sequencer shot (cam_D1):** 50° FOV zoom-in; cut to UI overlay.

## VFX & Interaction Stubs

### Niagara Systems

- `NS_HandTrail`
  - Input: world-space hand/controller position.
  - Emitter: ribbon with purple core, gold edge, lifetime 0.6 s.
  - Spawn rate: 180 p/s; use curl noise for subtle drift.

- `NS_DoorGlyph`
  - Trigger: door overlap event.
  - Emit: radial glyph mesh particles, dissolve material.
  - Duration: 1.2 s; ties to door animation timeline.

### Blueprint Hooks

- `BP_Conductor`
  - Variables: `HandTrailEmitter`, `APIClient` (HTTP component).
  - Event Graph:
    1. On Begin Play → spawn `NS_HandTrail` attached to hand socket.
    2. On Door Interaction → trigger `NS_DoorGlyph` + change door material emissive.

- `BP_TomeUI`
  - Widget component for page display.
  - Functions: `PopulateFromSymbolData(SymbolStruct)`.

## Data Integration

- REST endpoints to call:
  - `GET /symbols?query=` → list for grid.
  - `GET /symbols/{slug}` → detail card.
  - `GET /context?lat=&lon=` → context overlays.
- Prototype with `ExampleSymbol.json` (placed under `Content/Data/` for offline use).
- Unreal HTTP logic: use `HttpModule` (C++) or `VaRest` plugin (Blueprint).
- Refresh cadence: on door unlock fetch context; on tome open fetch symbol list.

## Deliverables for Vertical Slice

1. Unreal project with:
   - `Maps/NeonAscension_Greybox.umap`
   - Blueprint actors (`BP_Conductor`, `BP_GlyphDoor`, `BP_TomeUI`).
   - Niagara systems and placeholder materials.
2. Sequencer cinematic asset `Cine_NeonAscension` controlling cameras and key beats.
3. Recorded walkthrough (MP4/WebM) 45–60 seconds showing the full flow.
4. Checklist doc updated with progress (see shared tracker).

## Next Steps After Slice

- Replace blockout meshes with final art.
- Add animation retargeting for Conductor mocap.
- Hook real API data with pagination and error handling.
- Integrate audio (synth pad + ritual percussion + whisper VO).
