"""Search pipelines isolated from Tk, including process startup and decoding."""

import queue
import threading

from astroclocks.orbit_worker import OrbitCalculationJob
from astroclocks.settings import COORDINATE_SOURCE_APP


def calculate_search(generation, request, messages):
    from astroclocks.app import AstroClocksApp

    app = AstroClocksApp.__new__(AstroClocksApp)
    app.__dict__.update(request["snapshot"])
    context = request["search_context"]
    app.latitude = context["latitude"]
    app.longitude = context["longitude"]
    app.coordinate_source = COORDINATE_SOURCE_APP
    app.timezone_name = context["timezone_name"]
    app.daylight_saving_enabled = context["daylight_saving_enabled"]
    deliver = lambda _generation, payload: messages.put(("result", generation, payload))
    app._queue_star_search_results = deliver
    app._queue_deep_sky_search_results = deliver
    method = app._run_star_search if request["kind"] == "stars" else app._run_deep_sky_search
    try:
        method(generation, request["filters"], context,
               request["allow_online"], request["offline_note"])
    except Exception as exc:
        messages.put(("error", generation, str(exc)))


def start_search(app, kind, generation, filters, search_context, allow_online, offline_note, load_more=False):
    """Called on Tk; pass only values and poll an ordinary thread queue."""
    if not hasattr(app, "search_calculation_jobs"):
        app.search_calculation_jobs = {}
        app.search_calculations_closed = False

        def close(event):
            if event.widget is app.root:
                app.search_calculations_closed = True
                for active in app.search_calculation_jobs.values():
                    active.cancel()
                app.search_calculation_jobs.clear()

        app.root.bind("<Destroy>", close, add="+")
    previous = app.search_calculation_jobs.get(kind)
    if previous is not None:
        previous.cancel()
    request = {
        "kind": kind, "filters": dict(filters), "search_context": dict(search_context),
        "allow_online": allow_online, "offline_note": offline_note,
        "snapshot": {
            "online_load_more": load_more,
            "service_status": dict(getattr(app, "service_status", {})) if hasattr(app, "service_status") else None,
            "language": app.language, "network_online": app.network_online,
            "star_search_cached_stars": list(app.star_search_cached_stars) if kind == "stars" else [],
            "deep_sky_simbad_cached_objects": list(app.deep_sky_simbad_cached_objects) if kind == "deep_sky" else [],
        },
    }
    job = OrbitCalculationJob(generation, request, target=calculate_search,
                              name=f"AstroClocks-{kind}")
    app.search_calculation_jobs[kind] = job
    messages = queue.Queue()

    def poll():
        if app.search_calculations_closed or app.search_calculation_jobs.get(kind) is not job:
            return
        try:
            status, result_generation, payload = messages.get_nowait()
        except queue.Empty:
            app.root.after(50, poll)
            return
        app.search_calculation_jobs.pop(kind, None)
        if status == "error":
            key = "stars" if kind == "stars" else "objects"
            prefix = "star_search" if kind == "stars" else "deep_sky"
            payload = {key: [], "total": 0,
                       "note": app._tr(f"{prefix}.search_error", error=payload)}
        apply = app._apply_star_search_results if kind == "stars" else app._apply_deep_sky_search_results
        apply(result_generation, payload)

    app.root.after(50, poll)
    threading.Thread(target=job.run, args=(messages,), daemon=True).start()
