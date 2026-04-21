"""
Transit data parsing — shared between Raspberry Pi (CPython) and MicroPython (ESP32).

Works with plain dicts from json.loads() / ujson.loads(). No platform-specific
imports. The compute_minutes_fn argument keeps datetime handling in the caller.
"""


def extract_arrivals(api_response, compute_minutes_fn):
    """
    Extract a flat list of arrival dicts from a 511.org StopMonitoring response.

    Args:
        api_response: dict from json.loads() or ujson.loads() — NOT SimpleNamespace
        compute_minutes_fn: callable(utc_str: str) -> int
                            Returns minutes until arrival for an ISO 8601 UTC string.
                            Provided by the caller so datetime logic stays platform-specific.

    Returns:
        List of {'line_ref': str, 'minutes': int} in original API order,
        or [] on any parse error.
    """
    try:
        delivery = api_response['ServiceDelivery']['StopMonitoringDelivery']
        # The 511.org API returns StopMonitoringDelivery as either a dict or a
        # single-element list depending on the endpoint version.
        if isinstance(delivery, list):
            delivery = delivery[0]
        visits = delivery['MonitoredStopVisit']
    except (KeyError, IndexError, TypeError):
        return []

    arrivals = []
    for visit in visits:
        try:
            journey = visit['MonitoredVehicleJourney']
            line_ref = journey['LineRef']
            utc_str = journey['MonitoredCall']['ExpectedArrivalTime']
            minutes = compute_minutes_fn(utc_str)
            arrivals.append({'line_ref': line_ref, 'minutes': minutes})
        except (KeyError, TypeError):
            continue

    return arrivals
