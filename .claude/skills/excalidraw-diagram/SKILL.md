---
name: excalidraw-diagram
description: Draw architecture diagrams, flowcharts, mindmaps in Excalidraw via MCP. Use when user asks to draw, create, or update an Excalidraw diagram — system architecture, account schemas, flow diagrams, mindmaps. Handles proper element format, grouping, arrow bindings, and labels. Triggers on: "нарисуй схему", "создай диаграмму", "нарисуй в excalidraw", "создай схему в экскалидро", "нарисуй майндкарту", "обнови схему", "draw diagram", "create diagram", "update excalidraw".
user-invocable: true
---

# Excalidraw Diagram Skill

## ⚠️ CRITICAL — READ BEFORE WRITING ANY JSON

**NEVER call `create_view`** — text appears in the streaming preview but is COMPLETELY EMPTY in the actual exported diagram.
**ALWAYS call `export_to_excalidraw`** — this is the ONLY method that produces a working diagram with visible text.
**NEVER use `label` shorthand in JSON** — it only works in `create_view`. In `export_to_excalidraw`, ALL text MUST be a separate element with `containerId`.

> If you use `create_view` or `label` shorthand → every cell will be empty. No exceptions.

---

## Process

1. **Plan layout** — sketch on paper mentally: rows, columns, zones
2. **List all elements** with IDs before writing JSON
3. **Write JSON** — shapes first, then texts, then arrows
4. **Cross-check** — every connection listed in both directions
5. **Export** — call `export_to_excalidraw` with full JSON
6. **Open** — `start "" "https://excalidraw.com/#json=..."` on Windows

---

## JSON Wrapper

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "claude",
  "elements": [...],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  }
}
```

---

## Element Templates

### Rectangle with Text (ALWAYS pair these)

```json
{
  "type": "rectangle",
  "id": "box1",
  "x": 0, "y": 0, "width": 200, "height": 80,
  "angle": 0,
  "strokeColor": "#1971c2",
  "backgroundColor": "#e7f5ff",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "roundness": {"type": 3},
  "seed": 1001, "version": 1, "versionNonce": 1001,
  "isDeleted": false,
  "boundElements": [
    {"type": "text", "id": "t_box1"},
    {"type": "arrow", "id": "arr1"}
  ],
  "updated": 1234567890, "link": null, "locked": false, "frameId": null
},
{
  "type": "text",
  "id": "t_box1",
  "x": 5, "y": 5, "width": 190, "height": 70,
  "angle": 0,
  "strokeColor": "#1971c2",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 1, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100,
  "groupIds": [],
  "text": "Content line 1\nContent line 2",
  "fontSize": 14,
  "fontFamily": 2,
  "textAlign": "center",
  "verticalAlign": "middle",
  "baseline": 35,
  "containerId": "box1",
  "originalText": "Content line 1\nContent line 2",
  "lineHeight": 1.25,
  "roundness": null,
  "seed": 1002, "version": 1, "versionNonce": 1002,
  "isDeleted": false,
  "boundElements": [],
  "updated": 1234567890, "link": null, "locked": false, "frameId": null
}
```

### Arrow with Label (BIND BOTH WAYS)

```json
{
  "type": "arrow",
  "id": "arr1",
  "x": 200, "y": 40, "width": 100, "height": 0,
  "angle": 0,
  "strokeColor": "#1971c2",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100,
  "groupIds": [],
  "roundness": {"type": 2},
  "points": [[0, 0], [100, 0]],
  "startBinding": {"elementId": "box1", "focus": 0, "gap": 1},
  "endBinding": {"elementId": "box2", "focus": 0, "gap": 1},
  "startArrowhead": null,
  "endArrowhead": "arrow",
  "boundElements": [{"type": "text", "id": "t_arr1"}],
  "seed": 1003, "version": 1, "versionNonce": 1003,
  "isDeleted": false,
  "updated": 1234567890, "link": null, "locked": false, "frameId": null
},
{
  "type": "text",
  "id": "t_arr1",
  "x": 230, "y": 22, "width": 50, "height": 18,
  "angle": 0,
  "strokeColor": "#1971c2", "backgroundColor": "transparent",
  "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
  "roughness": 1, "opacity": 100, "groupIds": [],
  "text": "Label",
  "fontSize": 11, "fontFamily": 2,
  "textAlign": "center", "verticalAlign": "middle",
  "baseline": 10,
  "containerId": "arr1",
  "originalText": "Label",
  "lineHeight": 1.25, "roundness": null,
  "seed": 1004, "version": 1, "versionNonce": 1004,
  "isDeleted": false, "boundElements": [],
  "updated": 1234567890, "link": null, "locked": false, "frameId": null
}
```

### Grouped Zone (background + label + inner box — all move together)

```json
{"type": "rectangle", "id": "zone_bg", "groupIds": ["g_zone"],
 "backgroundColor": "#fff5f5", "strokeStyle": "dashed", "opacity": 100, ...},

{"type": "text", "id": "zone_lbl", "groupIds": ["g_zone"],
 "containerId": null, "text": "Zone Name", ...},

{"type": "rectangle", "id": "inner_box", "groupIds": ["g_zone"], ...},

{"type": "text", "id": "t_inner", "groupIds": ["g_zone"],
 "containerId": "inner_box", ...}
```

**Rule:** `containerId` for floating text = `null`. For bound text = parent shape/arrow ID.

---

## Arc Arrow (curved path over other elements)

```json
{
  "type": "arrow",
  "id": "arr_arc",
  "x": 355, "y": 148,
  "width": 395, "height": 52,
  "points": [[0, 52], [197, 0], [395, 52]],
  "startBinding": {"elementId": "box_left", "focus": 0, "gap": 1},
  "endBinding": {"elementId": "box_right", "focus": 0, "gap": 1},
  ...
}
```

Points are **relative to element's (x, y)**:
- `(x+0, y+52)` = start → aligns with source box
- `(x+197, y+0)` = arc top → peak of the curve
- `(x+395, y+52)` = end → aligns with target box

Choose `y` so arc peak stays in the gap between visual rows.

---

## Required Fields Checklists

### All elements
| Field | Value |
|-------|-------|
| type | rectangle / text / arrow / line |
| id | unique string |
| x, y | absolute position |
| width, height | size |
| angle | 0 |
| strokeColor | hex color |
| backgroundColor | hex color or "transparent" |
| fillStyle | "solid" |
| strokeWidth | 1 or 2 |
| strokeStyle | "solid" or "dashed" |
| roughness | 1 |
| opacity | 100 (use backgroundColor for tinted zones, NOT opacity) |
| groupIds | [] or ["group_name"] |
| roundness | {"type": 3} for shapes, null for text/arrows |
| seed | unique int |
| version, versionNonce | 1, same as seed |
| isDeleted | false |
| boundElements | [] or [{"type":"text","id":"..."}, {"type":"arrow","id":"..."}] |
| updated | 1234567890 |
| link, locked, frameId | null, false, null |

### Text elements (additional)
| Field | Value |
|-------|-------|
| text | content string |
| originalText | same as text |
| fontSize | 11–18 |
| fontFamily | 2 (handwritten feel) / 1 (normal) / 3 (mono) |
| textAlign | "center" or "left" |
| verticalAlign | "middle" |
| baseline | height/2 approx |
| containerId | null or parent element ID |
| lineHeight | 1.25 |

### Arrow elements (additional)
| Field | Value |
|-------|-------|
| points | [[0,0],[dx,dy]] relative to element x,y |
| startBinding | {elementId, focus: 0, gap: 1} |
| endBinding | {elementId, focus: 0, gap: 1} |
| startArrowhead | null |
| endArrowhead | "arrow" |

---

## Common Mistakes

| ❌ Wrong | ✅ Correct |
|----------|-----------|
| Floating label for arrow (containerId: null) | Text with containerId: "arrow_id" |
| Arrow not in shape's boundElements | Add {"type":"arrow","id":"..."} to both shapes |
| Text not in shape's boundElements | Add {"type":"text","id":"..."} to parent shape |
| Using opacity: 40 on zone background | Use opacity: 100 + light backgroundColor |
| Arrow points in absolute coordinates | Points are RELATIVE to arrow element's x,y |
| Floating zone label without groupIds | Add same groupIds as zone_bg + inner_box |
| groupIds inconsistent between zone+inner | All grouped elements share EXACT same groupId string |
| Duplicate IDs | Every element has a unique id |

---

## Color Palette

| Color | strokeColor | backgroundColor | Use for |
|-------|------------|-----------------|---------|
| Purple | #7950f2 | #f3f0ff | Owner, admin |
| Blue | #1971c2 | #e7f5ff | Workers, RDP |
| Green | #2f9e44 | #ebfbee | Type A contractors |
| Orange | #e67700 | #fff9db | Type B contractors |
| Red | #c92a2a | #fff5f5 | Isolated/admin server |
| Gray | #5c5f66 | #f1f3f5 | Storage, secondary |
| Teal | #0c8599 | #e3fafc | External services |

---

## Layout Guidelines

- **Row spacing:** 130–170px between visual rows
- **Element height:** 65–90px for actor boxes, 120–140px for detail boxes
- **Zone padding:** zone background 10px larger than inner box on each side
- **Zone label:** `y = zone_y + 5`, `x = zone_x + 5`, width = zone_width - 10
- **Inner box:** `x = zone_x + 10`, `y = zone_y + 20` (below zone label)
- **Arrow gap between zones:** 20–40px

---

## Pre-Export Checklist

- [ ] Every text element has containerId (shape ID or null for floating)
- [ ] Every shape's boundElements lists all connected texts + arrows
- [ ] Every arrow has startBinding AND endBinding
- [ ] Every arrow label text has containerId = arrow ID
- [ ] All elements in a group share the same groupId string
- [ ] No duplicate IDs
- [ ] Zone backgrounds have opacity: 100 (NOT 40/50)
- [ ] JSON is valid (no trailing commas, no comments)

---

## Typical Errors to Watch

### "Label stays in place when arrow moves"
Arrow labels MUST use `containerId: "arrow_id"`. Floating text (`containerId: null`) is not attached to the arrow.

### "Text is empty in exported diagram"
Using `label` shorthand only works in `create_view` (streaming). In `export_to_excalidraw`, always use explicit bound text elements.

### "Zone background doesn't move with account box"
All grouped elements must share the SAME `groupIds` value. Check: zone_bg, zone_lbl, inner_box, inner_text — all must have `"groupIds": ["same_group_id"]`.

### "Arrow stays when I move a block"
Arrow must have `startBinding`/`endBinding` AND the shape must list the arrow in its `boundElements`. Both directions required.

### "Diagonal arrow cuts across whole diagram"
Use L-shaped routing: `"points": [[0,0],[0,dy],[dx,dy],[dx,0]]` to route down then across, avoiding overlap with other elements.
