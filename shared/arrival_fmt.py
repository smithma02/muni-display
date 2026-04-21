"""
Arrival time formatting — shared between Raspberry Pi (CPython) and ESP32 (MicroPython).
No imports. Pure Python logic only.
"""


def format_arrival_times(arrivals, line_ref, max_display=12):
    """
    Format arrival times for a single line into a display string.

    Args:
        arrivals: list of dicts in original API order, each with:
                  {'line_ref': str, 'minutes': int}
                  The full list (all lines) is passed so first/last
                  position annotations are relative to all stop visits.
        line_ref: the line to filter for (case-insensitive match)
        max_display: maximum number of arrival times to include

    Returns:
        A string like "2, 5, 10" or "2🚀, 5, 10🦉" or "No arrivals"
    """
    line_ref_upper = line_ref.upper()
    total = len(arrivals)
    entries = []

    for i, arrival in enumerate(arrivals):
        if len(entries) >= max_display:
            break

        ref = arrival['line_ref'].upper()
        if ref != line_ref_upper:
            continue

        minutes = arrival['minutes']

        # Annotate OWL/express lines on first or last visit in the full list
        is_boundary = (i == 0 or i == total - 1)
        is_owl = ("OWL" in ref or ref == "91")
        is_express = ("R" in ref)
        show_annotation = (is_owl or is_express) and is_boundary

        if show_annotation and is_owl:
            entry = "{}🦉".format(minutes)
        elif show_annotation and is_express:
            entry = "{}🚀".format(minutes)
        else:
            entry = str(minutes)

        entries.append(entry)

    return ", ".join(entries) if entries else "No arrivals"
