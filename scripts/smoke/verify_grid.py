HOUR_CELL_H = 25
GRID_H = 600

cases = [
    ('00:00 - 00:00 (full day)', 0, 0),
    ('08:00 - 22:00', 8, 22),
    ('04:00 - 00:00', 4, 0),
    ('10:00 - 18:00', 10, 18),
]

for name, start, end in cases:
    eff_end = 23 if end <= start else end
    visible = list(range(start, eff_end + 1))
    n = len(visible)
    gridH = n * HOUR_CELL_H
    old_gridH = round(((eff_end - start) * 60 / 1440) * GRID_H) or GRID_H

    last_h = eff_end
    s_min = last_h * 60
    e_min = s_min + 60
    total_min = n * 60

    top = ((s_min - start * 60) / total_min) * gridH
    h_lesson = ((e_min - s_min) / total_min) * gridH

    visible_ok = top + h_lesson <= gridH + 0.01
    print(f"{name}:")
    print(f"  hours: {visible[0]}:00..{visible[-1]}:00 ({n}h)")
    print(f"  NEW gridH: {gridH}px  |  OLD gridH: {old_gridH}px (was clipped by {old_gridH - gridH}px)")
    print(f"  last hour: top={top}px h={h_lesson}px  |  bottom={top+h_lesson}px <= grid={gridH}px ? {'YES' if visible_ok else 'NO'}")
    print()
