import os
import json

from qt_api import QDialog
from qt_api import Qt
from classes.app import get_app
from classes.logger import log
from classes.ai_modules.__base_module import BaseModule

import openshot
from classes.query import File, Clip as QueryClip


class TimelineModule(BaseModule):
    panelText = "Files: To Timeline"   # text shown in left panel
    category = "General Modules"
    footer_text = None

    def __init__(self):
        super().__init__("Import File to Timeline", size=(120, 80))    # Text shown above the module box
        self.inputs = [(0, 30, "File Path"), (0, 50, "Track #"), (0, 70, "Start Time")]  # Inputs on the left
        self.outputs = []  # Outputs on the right
        self._create_ports()

    # This method is called when the module is executed. The inputs parameter will contain the data from connected modules.
    def run(self, inputs=None, workflow_context=None):
        log.info(f"Running Timeline module with inputs: {inputs}")
        # Call the base class run method to set the running state, handle any common logic, and get the initial result structure.
        result = super().run(inputs, workflow_context)  

        input_path = inputs.get(0, None)
        track_number = inputs.get(1, None)
        start_time = inputs.get(2, None)

        # Track # is mandatory
        if track_number is None:
            raise ValueError("Timeline module requires Track # (input 1).")

        # Validate input file
        if not input_path or not os.path.isfile(input_path):
            log.error("Input file not found in Timeline module: %s", input_path)
            result[0] = None
            return result

        # Default start time to 0 if not given
        if start_time is None:
            start_time = 0

        try:
            app = get_app()

            # Import into the current OpenShot project (creates File entry)
            app.window.files_model.add_files(input_path, quiet=True)

            # Fetch imported File object from project for exact reader/file_id/title
            file_obj = File.get(path=input_path)
            if not file_obj:
                # Fallback: try a direct filter scan if get(path=...) fails for any reason
                file_matches = list(File.filter(path=input_path))
                if file_matches:
                    file_obj = file_matches[0]

            if not file_obj:
                raise RuntimeError(f"Imported file but could not locate File object in project: {input_path}")

            # This module is for audio/video only. Images will not be added this fashion.
            media_type = (file_obj.data or {}).get("media_type")
            if media_type == "image":
                raise RuntimeError("TimelineModule only supports audio/video files (images are not supported).")

            reader = file_obj.data
            if not reader:
                raise RuntimeError("TimelineModule: imported File has no reader data")

            duration = float(reader.get("duration", 0.0) or 0.0)
            if duration <= 0:
                # Still required to set clip timing for correct placement
                raise RuntimeError(f"TimelineModule: could not determine clip duration for: {input_path}")

            # Build a clip JSON matching the GUI dialog behavior (AddToTimeline.accept).
            # The GUI sets: position (start), layer (track), file_id, title, reader,
            # duration, start=0, end=duration.
            clip = openshot.Clip(input_path)
            clip.Open()
            try:
                # Use the initial clip JSON as base and then override relevant keys.
                # (This avoids JSON schema guesses.)
                base_json = clip.Json()
                new_clip = json.loads(base_json)

                # Track mapping:
                # GUI “Track #” dropdown uses the project's layer object's `number` field (see add_to_timeline combobox population).
                # Some workflow authors may instead provide the dropdown index/order (1..N).
                #
                # We first try exact match to `layer['number']` (preferred).
                # If that fails, we fall back to mapping `track_number` as a 1-based index in the GUI ordering.
                app_project = get_app().project
                all_layers = app_project.get("layers") or []

                # Collect valid layer numbers in GUI order.
                # GUI ordering (from add_to_timeline_treeview) is effectively: reverse(sorted by 'number').
                # We mirror that ordering here so index-based mapping lands on the same track.
                valid_layers = [l for l in all_layers if isinstance(l, dict) and "number" in l]
                layer_numbers_sorted_desc = sorted(
                    [int(l.get("number")) for l in valid_layers],
                    reverse=True,
                )

                requested = int(track_number)

                if requested in layer_numbers_sorted_desc:
                    resolved_layer_number = requested
                    mapping_mode = "exact_layer_number_match"
                else:
                    # Fallback: treat requested as the *display track number* shown in the UI.
                    # OpenShot's default UI shows tracks in reverse order (e.g., [5,4,3,2,1]).
                    # If the UI shows N..1, then input=2 should map to the layer that appears as "2" in that list.
                    # With layer_numbers_sorted_desc = [N..1] in terms of display order, the mapping is:
                    #   resolved = layer_numbers_sorted_desc[N - requested]
                    n = len(layer_numbers_sorted_desc)
                    if 1 <= requested <= n:
                        resolved_layer_number = layer_numbers_sorted_desc[n - requested]
                        mapping_mode = "fallback_ui_display_track_number_to_layer_number"
                    else:
                        raise RuntimeError(
                            "TimelineModule: requested track_number does not match any project layer 'number' "
                            "and is out of range for UI display-track mapping. "
                            f"Requested track_number={track_number}; "
                            f"Available layer numbers={layer_numbers_sorted_desc}"
                        )

                log.info(
                    "TimelineModule track mapping: input_track_number=%s mapping_mode=%s resolved_layer_number=%s",
                    track_number,
                    mapping_mode,
                    resolved_layer_number,
                )

                new_clip["position"] = float(start_time)
                new_clip["layer"] = resolved_layer_number
                new_clip["file_id"] = file_obj.id
                filename = os.path.basename(input_path)
                new_clip["title"] = (file_obj.data or {}).get("name", filename)
                new_clip["reader"] = reader

                # Ensure full media duration
                new_clip["duration"] = duration
                new_clip["start"] = 0
                new_clip["end"] = duration

                # Persist to timeline/project by saving via the project's Query layer,
                # since `openshot.Clip` binding here does not implement `.save()`.
                qclip = QueryClip()
                qclip.data = new_clip
                qclip.save()
            finally:
                # Close the openshot.Clip wrapper we used to generate base JSON.
                clip.Close()

            # Ensure project duration grows to include inserted item
            win = getattr(app, "window", None)
            timeline_view = getattr(win, "timeline", None) if win else None
            extend_timeline = getattr(timeline_view, "_extend_timeline_to_fit_items", None)
            if callable(extend_timeline):
                try:
                    extend_timeline()
                except Exception:
                    log.warning("Failed to extend timeline after Add to Timeline", exc_info=1)

            result[0] = input_path
            log.info(
                "Imported file and inserted clip into timeline (track=%s, start=%s): %s",
                int(track_number),
                float(start_time),
                input_path,
            )

        except Exception as e:
            log.error("Failed to add file to project/timeline: %s", e, exc_info=1)
            result[0] = None

        super().run_after()
        return result
