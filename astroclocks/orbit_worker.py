"""ORB6/visibility computation in a process with no live Tk or ASCOM objects."""

import multiprocessing
import queue
import threading

from astroclocks.settings import COORDINATE_SOURCE_APP


class OrbitCalculationJob:
    """Own the process from a background thread; the UI only cancels an event."""

    def __init__(self, generation, request, target=None, name="AstroClocks-ORB6"):
        self.generation = generation
        self.request = request
        self.cancelled = threading.Event()
        self.target = target or calculate_orbit_catalog
        self.name = name

    def cancel(self):
        self.cancelled.set()

    def run(self, messages):
        if self.cancelled.is_set():
            return
        context = multiprocessing.get_context("spawn")
        results = context.Queue()
        process = context.Process(
            target=self.target,
            args=(self.generation, self.request, results),
            name=self.name, daemon=True,
        )
        try:
            # Windows serializes the request and initializes the child here.
            # This, and deserializing results, must not run on the Tk thread.
            process.start()
            while not self.cancelled.is_set():
                try:
                    message = results.get(timeout=0.1)
                except queue.Empty:
                    if not process.is_alive():
                        messages.put(("error", self.generation,
                                      f"{self.name} worker exited with code {process.exitcode}"))
                        return
                    continue
                messages.put(message)
                if message[0] in {"result", "error"}:
                    return
        except Exception as exc:
            if not self.cancelled.is_set():
                messages.put(("error", self.generation, str(exc)))
        finally:
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=1)
            process.close()
            results.close()


class _ProgressSink:
    def __init__(self, messages):
        self.messages = messages

    def put(self, update):
        self.messages.put(("progress", update[0], update))


def calculate_orbit_catalog(generation, request, messages):
    # Import only after the spawned interpreter is initialized. Creating this
    # calculation context never invokes __init__ or creates any Tk widgets.
    from astroclocks.app import AstroClocksApp

    context = request["search_context"]
    app = AstroClocksApp.__new__(AstroClocksApp)
    app.latitude = context["latitude"]
    app.longitude = context["longitude"]
    app.coordinate_source = COORDINATE_SOURCE_APP
    app.timezone_name = context["timezone_name"]
    app.daylight_saving_enabled = context["daylight_saving_enabled"]
    app.language = request["language"]
    app.double_orb6_orbit_index = request["orbit_index"]
    app.double_orbit_progress_queue = _ProgressSink(messages)
    try:
        visibility_context = app._double_visibility_context(context)
        enriched, _matched = app._enrich_double_star_orbits(
            request["catalog"], request["ephemeris_index"], request["orbit_index"],
            progress_callback=app._double_orbit_progress_callback(generation, "orbits"),
        )
        stars = app._filter_double_star_list(
            enriched, request["filters"], visibility_context,
            progress_callback=app._double_orbit_progress_callback(generation, "visibility"),
        )
        notes = list(request["notes"])
        count = sum(star.get("orb6_current_separation") is not None for star in stars)
        orbit_note = app._double_orb6_status_note(count, request["ephemeris_index"])
        if orbit_note:
            notes.append(orbit_note)
        payload = dict(request["result_metadata"], stars=stars, note="\n".join(notes))
        messages.put(("result", generation, payload))
    except Exception as exc:
        messages.put(("error", generation, str(exc)))
