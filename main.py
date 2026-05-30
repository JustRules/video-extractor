import subprocess
import sys
import json
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
        QComboBox,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".wmv",
    ".webm",
    ".flv",
    ".mpg",
    ".mpeg",
    ".mp4v",
    ".m4v",
}


def format_duration(ms: int) -> str:
    seconds = int(ms / 1000)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def find_ffmpeg() -> str | None:
    command = ["ffmpeg", "-version"]
    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
        return "ffmpeg"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


class VideoClipper(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Video Extractor")
        self.resize(1000, 640)

        self.video_folder: Path | None = None
        self.current_video: Path | None = None
        self.start_ms = 0
        self.end_ms = 0

        self.ffmpeg_exe = find_ffmpeg()

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(320, 240)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        self.player.setVideoOutput(self.video_widget)

        self.folder_label = QLabel("Aucun dossier sélectionné")
        self.video_list = QListWidget()
        self.video_list.itemActivated.connect(self.load_video)
        self.video_list.itemClicked.connect(self.load_video)

        self.start_label = QLabel("Début: 00:00:00")
        self.end_label = QLabel("Fin: 00:00:00")
        self.position_label = QLabel("Position: 00:00:00")

        self.scan_button = QPushButton("Scanner le dossier")
        self.scan_button.clicked.connect(self.select_folder)

        self.show_worked_only = False
        self.worked_videos_checkbox = QPushButton("Afficher travaillées")
        self.worked_videos_checkbox.setCheckable(True)
        self.worked_videos_checkbox.clicked.connect(self.toggle_worked_filter)
        self.worked_videos_checkbox.setToolTip("Afficher seulement les vidéos avec des sélections ou clips exportés")

        self.play_pause_button = QPushButton("Pause")
        self.mute_button = QPushButton("Mute")
        self.export_mode = QComboBox()
        self.export_mode.addItem("Propre (réencodage)", "clean")
        self.export_mode.addItem("Rapide (copy)", "fast")
        self.export_mode.setToolTip("Mode d'export : Propre réencode, Rapide copie les flux")
        self.set_start_button = QPushButton("Définir début")
        self.set_end_button = QPushButton("Définir fin")
        self.export_button = QPushButton("Exporter l'extrait")

        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.mute_button.clicked.connect(self.toggle_mute)
        self.set_start_button.clicked.connect(self.set_start)
        self.set_end_button.clicked.connect(self.set_end)
        self.export_button.clicked.connect(self.export_clip)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.seek_position)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Journaux d'export et informations...")

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.folder_label)
        scan_layout = QHBoxLayout()
        scan_layout.addWidget(self.scan_button)
        scan_layout.addWidget(self.worked_videos_checkbox)
        left_layout.addLayout(scan_layout)
        left_layout.addWidget(self.video_list)
        self.selections_label = QLabel("Sélections :")
        self.selections_list = QListWidget()
        self.selections_list.itemActivated.connect(self.goto_selection)
        sel_btn_layout = QHBoxLayout()
        self.add_selection_button = QPushButton("Ajouter sélection")
        self.remove_selection_button = QPushButton("Supprimer sélection")
        self.export_all_button = QPushButton("Exporter tout")
        self.add_selection_button.clicked.connect(self.add_selection)
        self.remove_selection_button.clicked.connect(self.remove_selection)
        self.export_all_button.clicked.connect(self.export_all_selections)
        sel_btn_layout.addWidget(self.add_selection_button)
        sel_btn_layout.addWidget(self.remove_selection_button)
        sel_btn_layout.addWidget(self.export_all_button)
        left_layout.addWidget(self.selections_label)
        left_layout.addWidget(self.selections_list)
        left_layout.addLayout(sel_btn_layout)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.play_pause_button)
        control_layout.addWidget(self.mute_button)
        control_layout.addWidget(self.export_mode)
        control_layout.addWidget(self.set_start_button)
        control_layout.addWidget(self.set_end_button)
        control_layout.addWidget(self.export_button)

        info_layout = QHBoxLayout()
        info_layout.addWidget(self.start_label)
        info_layout.addWidget(self.end_label)
        info_layout.addWidget(self.position_label)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.video_widget, stretch=5)
        right_layout.addWidget(self.position_slider)
        right_layout.addLayout(info_layout)
        right_layout.addLayout(control_layout)
        right_layout.addWidget(self.log_output, stretch=2)

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, stretch=2)
        main_layout.addLayout(right_layout, stretch=5)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.errorOccurred.connect(self.on_player_error)

        self.play_pause_button.setEnabled(False)
        self.mute_button.setEnabled(False)
        self.export_mode.setEnabled(False)
        self.statusBar().showMessage("Prêt")

        if self.ffmpeg_exe is None:
            self.log("FFmpeg introuvable. Ajoutez FFmpeg au PATH Windows.")
            self.export_button.setEnabled(False)
        # internal storage for multiple selections (list of (video_path, start_ms, end_ms))
        self.selections: list[tuple[str, int, int]] = []
        # track worked videos in JSON file
        self.worked_videos: set[str] = set()
        self.work_tracker_file: Path | None = None

    def log(self, message: str) -> None:
        self.log_output.append(message)

    def select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner un dossier vidéo")
        if not folder:
            return
        self.video_folder = Path(folder)
        self.folder_label.setText(str(self.video_folder))
        # Initialize work tracker file for this folder
        self.work_tracker_file = self.video_folder / ".work_tracker.json"
        self.load_work_tracker()
        self.scan_videos()

    def load_work_tracker(self) -> None:
        self.worked_videos = set()
        if self.work_tracker_file is None or not self.work_tracker_file.exists():
            return
        try:
            with self.work_tracker_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                self.worked_videos = set(data.get("worked_videos", []))
        except Exception as e:
            self.log(f"Erreur lecture tracker: {e}")

    def save_work_tracker(self) -> None:
        if self.work_tracker_file is None:
            return
        try:
            with self.work_tracker_file.open("w", encoding="utf-8") as f:
                json.dump({"worked_videos": sorted(list(self.worked_videos))}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"Erreur sauvegarde tracker: {e}")

    def mark_video_worked(self, video_path: Path) -> None:
        self.worked_videos.add(video_path.name)
        self.save_work_tracker()

    def is_video_worked(self, video_path: Path) -> bool:
        return video_path.name in self.worked_videos

    def toggle_worked_filter(self) -> None:
        self.show_worked_only = self.worked_videos_checkbox.isChecked()
        self.refresh_video_list()

    def refresh_video_list(self) -> None:
        self.video_list.clear()
        if self.video_folder is None:
            return
        files = sorted(
            [
                p
                for p in self.video_folder.iterdir()
                if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
            ],
            key=lambda p: p.name.lower(),
        )
        if not files:
            self.log("Aucune vidéo trouvée dans le dossier.")
            return
        for video in files:
            if self.show_worked_only and not self.is_video_worked(video):
                continue
            item = QListWidgetItem(video.name)
            item.setData(Qt.UserRole, str(video))
            # Mark worked videos in bold
            if self.is_video_worked(video):
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.video_list.addItem(item)
        displayed = self.video_list.count()
        self.log(f"{len(files)} vidéos trouvées, {displayed} affichées.")

    def scan_videos(self) -> None:
        if self.video_folder is None:
            return
        self.log(f"Scan du dossier {self.video_folder}")
        self.refresh_video_list()

    def load_video(self, item: QListWidgetItem | None = None) -> None:
        if item is None:
            item = self.video_list.currentItem()
            if item is None:
                return

        video_path = Path(item.data(Qt.UserRole))
        if not video_path.exists():
            self.log(f"Fichier introuvable: {video_path}")
            return

        self.current_video = video_path
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))
        self.player.play()
        self.statusBar().showMessage(f"Lecture: {video_path.name}")
        self.play_pause_button.setEnabled(True)
        self.mute_button.setEnabled(True)
        self.export_mode.setEnabled(True)
        self.play_pause_button.setText("Pause")
        self.start_ms = 0
        self.end_ms = 0
        self.update_markers()

    def set_start(self) -> None:
        if self.current_video is None:
            return
        self.start_ms = int(self.player.position())
        if self.end_ms and self.end_ms <= self.start_ms:
            self.end_ms = self.start_ms + 1000
        self.update_markers()
        self.log(f"Début défini sur {format_duration(self.start_ms)}")

    def set_end(self) -> None:
        if self.current_video is None:
            return
        self.end_ms = int(self.player.position())
        if self.end_ms <= self.start_ms:
            self.start_ms = max(0, self.end_ms - 1000)
        self.update_markers()
        self.log(f"Fin définie sur {format_duration(self.end_ms)}")

    def add_selection(self) -> None:
        if self.current_video is None:
            return
        if self.start_ms >= self.end_ms:
            QMessageBox.warning(self, "Intervalle incorrect", "Définissez d'abord un début et une fin valides.")
            return
        sel = (str(self.current_video), int(self.start_ms), int(self.end_ms))
        self.selections.append(sel)
        self.mark_video_worked(self.current_video)
        label = f"{Path(sel[0]).name}: {format_duration(sel[1])} → {format_duration(sel[2])}"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, json.dumps(list(sel)))
        self.selections_list.addItem(item)
        self.refresh_video_list()  # Refresh to show work status
        self.log(f"Sélection ajoutée: {label}")

    def remove_selection(self) -> None:
        item = self.selections_list.currentItem()
        if item is None:
            return
        data = item.data(Qt.UserRole)
        try:
            vid, start_s, end_s = json.loads(str(data))
        except Exception:
            vid = start_s = end_s = None
        # remove from internal list
        if vid is not None:
            self.selections = [s for s in self.selections if not (s[0] == vid and s[1] == start_s and s[2] == end_s)]
        self.selections_list.takeItem(self.selections_list.row(item))
        self.refresh_video_list()  # Refresh to update work status
        self.log("Sélection supprimée")

    def goto_selection(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        try:
            vid, start_s, end_s = json.loads(str(data))
        except Exception:
            return
        # load the corresponding video and jump to start
        video_path = Path(vid)
        if not video_path.exists():
            self.log(f"Fichier introuvable pour sélection: {video_path}")
            return
        # set source and play from selection start
        self.current_video = video_path
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))
        self.player.setPosition(int(start_s))
        self.player.play()
        self.play_pause_button.setText("Pause")

    def update_markers(self) -> None:
        self.start_label.setText(f"Début: {format_duration(self.start_ms)}")
        self.end_label.setText(f"Fin: {format_duration(self.end_ms)}")

    def on_position_changed(self, position: int) -> None:
        self.position_label.setText(f"Position: {format_duration(position)}")
        if self.player.duration() > 0:
            self.position_slider.blockSignals(True)
            self.position_slider.setValue(position)
            self.position_slider.blockSignals(False)

    def on_duration_changed(self, duration: int) -> None:
        self.position_slider.setRange(0, duration)

    def seek_position(self, position: int) -> None:
        self.player.setPosition(position)

    def on_media_status_changed(self, status) -> None:
        if status == QMediaPlayer.InvalidMedia:
            self.log("Statut média invalide : impossible de lire cette vidéo.")
        elif status == QMediaPlayer.NoMedia:
            self.log("Aucun média chargé.")
        elif status == QMediaPlayer.LoadedMedia:
            self.log("Vidéo chargée avec succès.")

    def on_player_error(self, error, error_string: str = "") -> None:
        if error != QMediaPlayer.NoError:
            message = error_string or self.player.errorString()
            self.log(f"Erreur lecture: {message}")
            self.statusBar().showMessage(f"Erreur: {message}")

    def toggle_play_pause(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_pause_button.setText("Play")
        else:
            self.player.play()
            self.play_pause_button.setText("Pause")

    def toggle_mute(self) -> None:
        muted = not self.audio_output.isMuted()
        self.audio_output.setMuted(muted)
        self.mute_button.setText("Unmute" if muted else "Mute")

    def export_clip(self) -> None:
        # Export the current single selection (start_ms/end_ms)
        self.export_interval(self.start_ms, self.end_ms)

    def export_interval(self, start_ms: int, end_ms: int, suffix: str | None = None, video_path: str | None = None) -> bool:
        # video_path overrides current_video when exporting selections from other files
        video = Path(video_path) if video_path is not None else self.current_video
        if video is None:
            QMessageBox.warning(self, "Aucun fichier", "Sélectionnez une vidéo avant d'exporter.")
            return False
        if not video.exists():
            QMessageBox.warning(self, "Fichier introuvable", f"Vidéo introuvable: {video}")
            return False
        if start_ms >= end_ms:
            QMessageBox.warning(self, "Intervalle incorrect", "Intervalle invalide.")
            return False

        self.mark_video_worked(video)
        output_dir = video.parent / "clips"
        output_dir.mkdir(parents=True, exist_ok=True)

        start_label = format_duration(start_ms).replace(":", "-")
        end_label = format_duration(end_ms).replace(":", "-")
        suffix = suffix or f"{start_label}_{end_label}"
        output_file = output_dir / f"{video.stem}_{suffix}{video.suffix}"
        self.log(f"Export en cours: {output_file.name}")

        start_seconds = start_ms / 1000.0
        duration_seconds = (end_ms - start_ms) / 1000.0

        # Determine chosen export mode: 'clean' = re-encode, 'fast' = copy
        mode = "clean"
        try:
            mode = self.export_mode.currentData()
        except Exception:
            pass

        result = None

        if mode == "fast":
            command = [
                self.ffmpeg_exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{start_seconds:.3f}",
                "-i",
                str(video),
                "-t",
                f"{duration_seconds:.3f}",
                "-c",
                "copy",
                str(output_file),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0 or not output_file.exists():
                self.log("Copie rapide échouée, tentative de réencodage propre...")
                mode = "clean"

        if mode == "clean":
            command = [
                self.ffmpeg_exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{start_seconds:.3f}",
                "-i",
                str(video),
                "-t",
                f"{duration_seconds:.3f}",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                "-fflags",
                "+genpts",
                str(output_file),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0 or not output_file.exists():
                self.log("Ré-encodage échoué, tentative de copie en secours...")
                command = [
                    self.ffmpeg_exe,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    f"{start_seconds:.3f}",
                    "-i",
                        str(video),
                    "-t",
                    f"{duration_seconds:.3f}",
                    "-c",
                    "copy",
                    str(output_file),
                ]
                result = subprocess.run(command, capture_output=True, text=True)

        if result is None or result.returncode != 0:
            self.log(f"Erreur FFmpeg: {result.stderr.strip() if result is not None else 'unknown'}")
            QMessageBox.critical(self, "Échec de l'export", "L'export a échoué. Vérifiez les journaux.")
            return False

        self.log(f"Export terminé: {output_file}")
        return True

    def export_all_selections(self) -> None:
        if not self.selections:
            QMessageBox.information(self, "Aucune sélection", "Aucune sélection à exporter.")
            return

        # Group selections by source video
        groups: dict[str, list[tuple[int, int]]] = {}
        for vid, s, e in self.selections:
            groups.setdefault(vid, []).append((s, e))

        for vid, intervals in groups.items():
            video = Path(vid)
            if not video.exists():
                self.log(f"Fichier introuvable pour export groupé: {video}")
                continue

            self.mark_video_worked(video)
            output_dir = video.parent / "clips"
            output_dir.mkdir(parents=True, exist_ok=True)
            final_name = f"{video.stem}_grouped{video.suffix}"
            final_path = output_dir / final_name

            # create temp dir for segments
            tmp_dir = output_dir / f".tmp_group_{uuid.uuid4().hex}"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            seg_paths: list[Path] = []

            mode = "clean"
            try:
                mode = self.export_mode.currentData()
            except Exception:
                pass

            failed = False
            for idx, (s, e) in enumerate(intervals, start=1):
                seg_path = tmp_dir / f"seg{idx}{video.suffix}"
                ok = self._render_segment(video, s, e, seg_path, mode=mode)
                if not ok:
                    failed = True
                    break
                seg_paths.append(seg_path)

            if failed or not seg_paths:
                self.log(f"Export groupé échoué pour {video.name}")
                # cleanup tmp
                for p in seg_paths:
                    try:
                        p.unlink()
                    except Exception:
                        pass
                try:
                    tmp_dir.rmdir()
                except Exception:
                    pass
                continue

            # write concat file
            list_file = tmp_dir / "files.txt"
            with list_file.open("w", encoding="utf-8") as f:
                for p in seg_paths:
                    # concat demuxer expects paths in the form: file 'path'
                    f.write(f"file '{p.as_posix()}'\n")

            # try concat with copy
            cmd = [
                self.ffmpeg_exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(final_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0 or not final_path.exists():
                # fallback: re-encode the concatenation to ensure compatibility
                self.log(f"Concat direct échoué pour {video.name}, réencodage final...")
                cmd = [
                    self.ffmpeg_exe,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_file),
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    str(final_path),
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)

            if res.returncode != 0:
                self.log(f"Échec concat pour {video.name}: {res.stderr}")
            else:
                self.log(f"Export groupé terminé: {final_path}")

            # cleanup tmp files
            for p in seg_paths:
                try:
                    p.unlink()
                except Exception:
                    pass
            try:
                list_file.unlink()
            except Exception:
                pass
            try:
                tmp_dir.rmdir()
            except Exception:
                pass

        QMessageBox.information(self, "Export terminé", "Export groupé des sélections terminé.")

    def _render_segment(self, video: Path, start_ms: int, end_ms: int, out_path: Path, mode: str = "clean") -> bool:
        start_seconds = start_ms / 1000.0
        duration_seconds = (end_ms - start_ms) / 1000.0
        if mode == "fast":
            cmd = [
                self.ffmpeg_exe,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{start_seconds:.3f}",
                "-i",
                str(video),
                "-t",
                f"{duration_seconds:.3f}",
                "-c",
                "copy",
                str(out_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and out_path.exists():
                return True
            # fallthrough to clean

        # clean render (re-encode segment)
        cmd = [
            self.ffmpeg_exe,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start_seconds:.3f}",
            "-i",
            str(video),
            "-t",
            f"{duration_seconds:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            str(out_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0 and out_path.exists()


def main() -> int:
    app = QApplication(sys.argv)
    window = VideoClipper()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
