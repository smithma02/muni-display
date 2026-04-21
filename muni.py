import requests
import json
from utils import *
from shared.transit_data import extract_arrivals
from shared.arrival_fmt import format_arrival_times


def get_stop_data(stop_id, agency, api_key):
    url = (
        f"https://api.511.org/transit/StopMonitoring?"
        f"api_key={api_key}&agency={agency}&stopcode={stop_id}&format=json&MaximumStopVisits=30"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response_text = response.content.decode('utf-8-sig')
        return json.loads(response_text)

    except requests.exceptions.RequestException as e:
        print(f"Network error when fetching stop {stop_id}: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON parsing error for stop {stop_id}: {e}")
    except Exception as e:
        print(f"Unexpected error for stop {stop_id}: {e}")

    return None


def get_formatted_arrival_times(stop_response, lineRef, max_visits=12):
    """
    Returns a formatted arrival time string for a given line at a stop.

    Args:
        stop_response: dict from get_stop_data() (plain JSON, no SimpleNamespace)
        lineRef: line reference string to filter for (e.g. "N", "Red-N")
        max_visits: max arrivals to include in output

    Returns:
        A string like "2, 5, 10" or "2🚀, 5, 10🦉" or "No arrivals"
    """
    if not stop_response:
        print("No stop data received.")
        return "No arrivals"

    arrivals = extract_arrivals(stop_response, time_until_utc_min)
    return format_arrival_times(arrivals, lineRef, max_display=max_visits)


def render_muni_times_to_html(formattedTimes, template_name='hello.html', debug=False):
    """
    Renders Muni times into HTML and passes to image renderer.

    :param formattedTimes: dict of data to render into template
    :param template_name: Jinja template file
    :param debug: If True, saves rendered HTML and BMP image to disk
    :return: PIL.Image.Image object or None
    """
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_name)
    html_output = template.render(**formattedTimes)

    if debug:
        with open("hello-out.html", "w") as f:
            f.write(html_output)
        print("📝 Saved debug HTML: hello-out.html")

    print("🧠 Rendered HTML context:", formattedTimes)

    return convert_html_to_image_weasy(html_output, debug=debug)
