from qt_api import (
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QFileDialog,
    QLabel, QComboBox, QPushButton, QVBoxLayout, QHBoxLayout,
    Qt
)
from classes.logger import log
from classes.app import get_app
from classes.ai_modules.__base_module import BaseModule

import json
import os
import tempfile
import shutil
import subprocess

import openshot

class ClipModule(BaseModule):

    panelText = "Clip Audio/Video"   #text shown in left panel
    category = "General Modules"
    footer_text = None
    output_path = ""  # Example setting for the module

    def __init__(self):
        super().__init__("Clip", size=(120, 80))    # Text shown in the module box
        self.inputs = [(0, 30, "Source Path"), (0, 50, "Start"), (0, 70, "End")]      # Inputs on the left
        self.outputs = [(120, 40, "Output Path")] # Outputs on the right
        self._create_ports()
        self.output_path = ""
        self.output_format = ""  # empty = same as input

    # This method is called when the module is executed. The inputs parameter will contain the data from connected modules.
    def run(self, inputs=None, workflow_context=None):
        log.info(f"Running Clip module with inputs: {inputs}")
        # Call the base class run method to set the running state, handle any common logic, and get the initial result structure.
        result = super().run(inputs, workflow_context)  

        ## Your module's processing logic goes here.
        try:
            start = inputs.get(1, 0)
            end = inputs.get(2, None)
            input_path = inputs.get(0, None)
            if not input_path or not os.path.isfile(input_path):
                log.error("Input file not found in Clip module: %s", input_path)
                result[0] = None
                return result

            output_dir = self.output_path or tempfile.gettempdir()
            os.makedirs(output_dir, exist_ok=True)

            # Determine output extension based on selected format (empty == same as input)
            selected = (getattr(self, 'output_format', '') or '').lower()
            audio_formats = ("wav", "flac", "mp3", "m4a", "aac")
            video_formats = ("mp4", "avi", "mov", "mkv", "webm")
            orig_ext = os.path.splitext(input_path)[1].lower()

            if not selected:
                output_ext = orig_ext
            elif selected in audio_formats:
                output_ext = f".{selected}"
            elif selected in video_formats:
                output_ext = f".{selected}"
            else:
                output_ext = orig_ext

            root = os.path.splitext(os.path.basename(input_path))[0]
            output_file = os.path.join(output_dir, f"{root}_clip{output_ext}")
            index = 1
            while os.path.exists(output_file):
                output_file = os.path.join(output_dir, f"{root}_clip_{index}{output_ext}")
                index += 1

            clip = openshot.Clip(input_path)
            clip.Open()
            try:
                reader = clip.Reader()
                metadata = json.loads(reader.Json() or "{}")
                log.info("Clip metadata: %s", metadata)
                fps_meta = metadata.get("fps", {"num": 30, "den": 1})
                # Compute numeric FPS value for time->frame conversions
                try:
                    fps_num = int(fps_meta.get("num", 30))
                    fps_den = int(fps_meta.get("den", 1) or 1)
                    fps_value = float(fps_num) / float(fps_den)
                except Exception:
                    fps_value = 30.0

                max_frame = int(metadata.get("video_length", metadata.get("audio_length", 0)) or 0)
                if max_frame <= 0:
                    raise RuntimeError("Unable to determine clip frame length")

                start_seconds = float(start or 0)
                try:
                    end_value = float(end) if end is not None else None
                except Exception:
                    end_value = None

                if end_value is None or end_value < 0:
                    end_seconds = max_frame / float(fps_value)
                else:
                    end_seconds = end_value

                start_seconds = max(0.0, start_seconds)
                end_seconds = max(start_seconds, end_seconds)

                # Use the same frame math as other exporters: start_frame starts at 1
                start_frame = max(1, int(round(start_seconds * fps_value)) + 1)
                end_frame = max(start_frame - 1, min(max_frame, int(round(end_seconds * fps_value))))
                log.info("Clip time range: %s - %s seconds; frames %s - %s (fps=%s)",
                         start_seconds, end_seconds, start_frame, end_frame, fps_value)
                if start_frame > end_frame:
                    raise RuntimeError("Clip start time must be before end time")

                # Determine output type (audio or video)
                output_ext = os.path.splitext(output_file)[1].lower()
                audio_codec = "aac"
                if output_ext == ".flac":
                    audio_codec = "flac"
                elif output_ext == ".mp3":
                    audio_codec = "libmp3lame"
                elif output_ext == ".wav":
                    audio_codec = "pcm_s16le"

                writer = openshot.FFmpegWriter(output_file)
                has_video = bool(metadata.get("has_video"))
                has_audio = bool(metadata.get("has_audio"))

                selected = (getattr(self, 'output_format', '') or '').lower()
                audio_formats = ("wav", "flac", "mp3", "m4a", "aac")
                video_formats = ("mp4", "avi", "mov", "mkv", "webm")

                if selected in audio_formats:
                    output_is_audio = True
                    output_is_video = False
                elif selected in video_formats:
                    output_is_video = True
                    output_is_audio = False
                else:
                    # same as input
                    output_is_video = has_video
                    output_is_audio = has_audio and not has_video

                # If user requested audio output
                if output_is_audio:
                    # If source has no audio, fail
                    if not has_audio:
                        log.error("Cannot produce audio output: source has no audio")
                        result[0] = None
                        clip.Close()
                        super().run_after()
                        return result

                    ffmpeg_path = shutil.which("ffmpeg")
                    if not ffmpeg_path:
                        raise RuntimeError("ffmpeg not found in PATH; required for audio trimming/conversion")

                    # Choose codec mapping for common audio extensions
                    codec_map = {
                        ".wav": "pcm_s16le",
                        ".flac": "flac",
                        ".mp3": "libmp3lame",
                        ".m4a": "aac",
                        ".aac": "aac",
                    }
                    acodec = codec_map.get(output_ext, None)

                    ff_args = [
                        ffmpeg_path,
                        "-y",
                        "-analyzeduration", "5000000",
                        "-probesize", "5000000",
                        "-ss", str(start_seconds),
                        "-to", str(end_seconds),
                        "-i", input_path,
                    ]
                    # If input is video, strip video stream when extracting audio
                    if has_video:
                        ff_args += ["-vn"]

                    if acodec:
                        ff_args += ["-acodec", acodec]
                    else:
                        ff_args += ["-c", "copy"]
                    ff_args += [output_file]

                    log.info("Running ffmpeg for audio extraction/trim: %s", " ".join(ff_args))
                    proc = subprocess.run(ff_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if proc.returncode != 0 or not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                        log.error("ffmpeg failed: returncode=%s stderr=%s", proc.returncode, proc.stderr.decode(errors='replace'))
                        result[0] = None
                    else:
                        result[0] = output_file
                    log.info(f"Clip module outputs: {result}")
                    clip.Close()
                    super().run_after()
                    return result

                # If user requested video output but source is audio-only -> error
                if output_is_video and not has_video:
                    log.error("Cannot produce video output from an audio-only source")
                    result[0] = None
                    clip.Close()
                    super().run_after()
                    return result

                # If output is AVI, use a compatible codec and explicit pixel format
                if output_ext == ".avi":
                    ffmpeg_path = shutil.which("ffmpeg")
                    if not ffmpeg_path:
                        raise RuntimeError("ffmpeg not found in PATH; required for AVI transcoding")

                    ff_args = [
                        ffmpeg_path,
                        "-y",
                        "-analyzeduration", "5000000",
                        "-probesize", "5000000",
                        "-ss", str(start_seconds),
                        "-to", str(end_seconds),
                        "-i", input_path,
                        "-c:v", "mpeg4",
                        "-pix_fmt", "yuv420p",
                    ]
                    if has_audio:
                        ff_args += ["-c:a", "libmp3lame"]
                    else:
                        ff_args += ["-an"]
                    ff_args += [output_file]

                    log.info("Running ffmpeg for AVI output: %s", " ".join(ff_args))
                    proc = subprocess.run(ff_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if proc.returncode != 0 or not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                        log.error("AVI ffmpeg failed: returncode=%s stderr=%s", proc.returncode, proc.stderr.decode(errors='replace'))
                        result[0] = None
                    else:
                        result[0] = output_file
                    log.info(f"Clip module outputs: {result}")
                    clip.Close()
                    super().run_after()
                    return result

                if has_video:
                    pixel_ratio_meta = metadata.get("pixel_ratio", {"num": 1, "den": 1})
                    # Build openshot Fraction for fps
                    fps_meta = metadata.get("fps", {"num": 30, "den": 1})
                    fps_fraction = openshot.Fraction(int(fps_meta.get("num", 30)), int(fps_meta.get("den", 1)))
                    writer.SetVideoOptions(
                        True,
                        "libx264",
                        fps_fraction,
                        int(metadata.get("width", 1280)),
                        int(metadata.get("height", 720)),
                        openshot.Fraction(int(pixel_ratio_meta.get("num", 1)), int(pixel_ratio_meta.get("den", 1))),
                        False,
                        False,
                        22,
                    )
                    writer.PrepareStreams()

                if has_audio:
                    writer.SetAudioOptions(
                        True,
                        audio_codec,
                        int(metadata.get("sample_rate", 48000)),
                        int(metadata.get("channels", 2)),
                        int(metadata.get("channel_layout", openshot.LAYOUT_STEREO)),
                        int(metadata.get("audio_bit_rate", 192000)) if audio_codec not in ("flac", "pcm_s16le") else 0,
                    )
                    writer.PrepareStreams()

                writer.Open()
                frames_written = 0
                for frame_number in range(start_frame, end_frame + 1):
                    frame = reader.GetFrame(frame_number)
                    if frame is None:
                        continue
                    writer.WriteFrame(frame)
                    frames_written += 1
                writer.Close()

                if frames_written == 0:
                    # Remove empty output and report failure
                    try:
                        if os.path.exists(output_file):
                            os.remove(output_file)
                    except Exception:
                        pass
                    log.error("No frames written for clip; output removed: %s", output_file)
                    result[0] = None
                else:
                    result[0] = output_file
                    log.info(f"Clip module outputs: {result}")
            finally:
                clip.Close()
        except Exception as e:
            log.error("Error processing file in Clip module: %s", e)
            result[0] = None
        ##

        super().run_after()  # Reset running state after execution
        return result
    
    # This method is called when the user double-clicks the module. You can create a dialog here for user settings.
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            dialog_parent = None
            scene = self.scene()
            if scene and scene.views():
                dialog_parent = scene.views()[0]

            dialog = QDialog(dialog_parent)
            dialog.setWindowTitle(self.panelText)
            dialog.setMinimumSize(320, 180)

            current_project_path = getattr(get_app().project, "current_filepath", None)
            project_dir = os.path.dirname(current_project_path) if current_project_path else None
            output_initial = self.output_path or project_dir or ""

            main_layout = QVBoxLayout(dialog)
            try:
                help_text = (
                    "Clips audio/video files. Start=0 if not connected. If end=-1 or not connected,\n"
                    "the file will be clipped from the start input to the end of the original file.\n"
                    "If the input file is video but the output format is audio-only, the audio stream will be extracted.\n"
                    "If the input file is audio-only but the output format is video, an error will be raised.\n"
                )
                help_label = QLabel(help_text, dialog)
                main_layout.addWidget(help_label)
            except Exception as e:
                log.error("Error creating help label in Clip module dialog: %s", e)

            form_layout = QFormLayout()
            form_layout.setLabelAlignment(Qt.AlignLeft)

            output_layout = QHBoxLayout()
            output_label = QLabel(get_app()._tr("Output directory:"), dialog)
            self.output_dir_line = QLineEdit(output_initial, dialog)
            self.output_dir_line.setReadOnly(True)
            output_button = QPushButton(get_app()._tr("Browse..."), dialog)

            def choose_output_dir():
                start_dir = project_dir or os.path.expanduser("~")
                path = QFileDialog.getExistingDirectory(dialog, get_app()._tr("Select Output Directory"), start_dir)
                if path:
                    self.output_dir_line.setText(path)

            output_button.clicked.connect(choose_output_dir)
            output_layout.addWidget(self.output_dir_line)
            output_layout.addWidget(output_button)
            form_layout.addRow(output_label, output_layout)

            # Output format selection (audio/video) with separators
            format_label = QLabel(get_app()._tr("Output format:"), dialog)
            self.format_combo = QComboBox(dialog)
            # Default option: same as input
            same_text = get_app()._tr("Same as input")
            self.format_combo.addItem(same_text)

            # Audio formats header (disabled)
            self.format_combo.addItem(get_app()._tr("Audio Formats:"))
            try:
                self.format_combo.model().item(self.format_combo.count()-1).setEnabled(False)
            except Exception:
                pass
            for fmt in ("wav", "flac", "mp3", "m4a", "aac"):
                self.format_combo.addItem(fmt)

            # Video formats header (disabled)
            self.format_combo.addItem(get_app()._tr("Video Formats:"))
            try:
                self.format_combo.model().item(self.format_combo.count()-1).setEnabled(False)
            except Exception:
                pass
            for fmt in ("mp4", "avi", "mov", "mkv", "webm"):
                self.format_combo.addItem(fmt)

            # Make "Same as input" the default
            self.format_combo.setCurrentIndex(0)

            form_layout.addRow(format_label, self.format_combo)
            main_layout.addLayout(form_layout)

            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            main_layout.addWidget(button_box)

            if dialog.exec_() == QDialog.Accepted:
                self.output_path = self.output_dir_line.text().strip() or tempfile.gettempdir()
                # Persist chosen format (empty string == same as input)
                selected = self.format_combo.currentText() if hasattr(self, 'format_combo') else ""
                if selected == same_text:
                    self.output_format = ""
                else:
                    self.output_format = (selected or "").lower()
                log.info("Clip module output directory: %s; format: %s", self.output_path, self.output_format)
            event.accept()
        super().mouseDoubleClickEvent(event)

    def get_settings(self):
        return {"output_path": self.output_path, "output_format": self.output_format}

    def set_settings(self, settings):
        self.output_path = settings.get("output_path", "")
        self.output_format = settings.get("output_format", "")