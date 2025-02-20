# coding=utf-8
"""This module has the main GUI interaction logic for AnimationWorkbench."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

# This will make the QGIS use a world projection and then move the center
# of the CRS sequentially to create a spinning globe effect
import os
import tempfile
from typing import Optional
from functools import partial

# This import is to enable SIP API V2
# noinspection PyUnresolvedReferences
import qgis  # NOQA
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from qgis.PyQt.QtCore import pyqtSlot, QUrl
from qgis.PyQt.QtGui import QIcon, QPixmap, QImage
from qgis.PyQt.QtWidgets import (
    QStyle,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QVBoxLayout,
)
from qgis.PyQt.QtXml import QDomDocument, QDomElement
from qgis.core import (
    QgsPointXY,
    QgsExpressionContextUtils,
    QgsProject,
    QgsMapLayerProxyModel,
    QgsReferencedRectangle,
    QgsApplication,
    QgsExpressionContextGenerator,
    QgsPropertyCollection,
    QgsExpressionContext,
    QgsVectorLayer,
)
from qgis.gui import QgsExtentWidget, QgsPropertyOverrideButton

from .settings import set_setting, setting
from .utilities import get_ui_class, resources_path
from .animation_controller import (
    MapMode,
    AnimationController,
    InvalidAnimationParametersException,
)
from .movie_creator import MovieCreationTask, MovieFormat

FORM_CLASS = get_ui_class("animation_workbench_base.ui")


class DialogExpressionContextGenerator(QgsExpressionContextGenerator):
    def __init__(self):
        super().__init__()
        self.layer = None

    def set_layer(self, layer: QgsVectorLayer):
        self.layer = layer

    def createExpressionContext(self) -> QgsExpressionContext:
        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.globalScope())
        context.appendScope(
            QgsExpressionContextUtils.projectScope(QgsProject.instance())
        )
        if self.layer:
            context.appendScope(self.layer.createExpressionContextScope())
        return context


class AnimationWorkbench(QDialog, FORM_CLASS):
    """Dialog implementation class Animation Workbench class."""

    def __init__(self, parent=None, iface=None, render_queue=None):
        """Constructor for the workbench dialog.

        :param parent: Parent widget of this dialog.
        :type parent: QWidget

        :param iface: QGIS Plugin Interface.
        :type iface: QgsInterface

        :param render_queue: Render queue to processing each frame.
        :type render_queue: RenderQueue
        """
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.expression_context_generator = DialogExpressionContextGenerator()
        self.main_stack.setCurrentIndex(0)
        self.extent_group_box = QgsExtentWidget(
            None, QgsExtentWidget.ExpandedStyle
        )
        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.extent_group_box)
        self.extent_widget_container.setLayout(vbox_layout)

        self.render_queue = render_queue
        self.setWindowTitle(self.tr("Animation Workbench"))
        icon = resources_path("img", "icons", "animation-workshop.svg")
        self.setWindowIcon(QIcon(icon))
        self.parent = parent
        self.iface = iface

        self.data_defined_properties = QgsPropertyCollection()

        self.extent_group_box.setMapCanvas(self.iface.mapCanvas())
        self.scale_range.setMapCanvas(self.iface.mapCanvas())

        self.output_log_text_edit.append(
            "Welcome to the QGIS Animation Workbench"
        )
        self.output_log_text_edit.append("© Tim Sutton, Feb 2022")

        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        # ok_button.clicked.connect(self.accept)
        ok_button.setText("Run")
        ok_button.setEnabled(False)

        self.cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        self.cancel_button.clicked.connect(self.cancel_processing)

        # place where working files are stored
        self.work_directory = tempfile.gettempdir()
        self.frame_filename_prefix = "animation_workbench"
        # place where final products are stored
        output_file = setting(
            key="output_file", default="", prefer_project_setting=True
        )
        if output_file:
            self.movie_file_edit.setText(output_file)
            ok_button.setEnabled(True)

        self.movie_file_button.clicked.connect(self.set_output_name)

        music_file = setting(
            key="music_file", default="", prefer_project_setting=True
        )
        if music_file:
            self.music_file_edit.setText(music_file)
        self.music_file_button.clicked.connect(self.choose_music_file)

        # Work around for not being able to set the layer
        # types allowed in the QgsMapLayerSelector combo
        # See https://github.com/qgis/QGIS/issues/38472#issuecomment-715178025
        self.layer_combo.setFilters(
            QgsMapLayerProxyModel.PointLayer
            | QgsMapLayerProxyModel.LineLayer
            | QgsMapLayerProxyModel.PolygonLayer
        )
        self.layer_combo.layerChanged.connect(self._layer_changed)

        prev_layer_id, ok = QgsProject.instance().readEntry(
            "animation", "layer_id"
        )
        if prev_layer_id:
            layer = QgsProject.instance().mapLayer(prev_layer_id)
            if layer:
                self.layer_combo.setLayer(layer)

        prev_data_defined_properties_xml, _ = QgsProject.instance().readEntry(
            "animation", "data_defined_properties"
        )
        if prev_data_defined_properties_xml:
            doc = QDomDocument()
            doc.setContent(prev_data_defined_properties_xml.encode())
            elem = doc.firstChildElement("data_defined_properties")
            self.data_defined_properties.readXml(
                elem, AnimationController.DYNAMIC_PROPERTIES
            )

        self.extent_group_box.setOutputCrs(QgsProject.instance().crs())
        self.extent_group_box.setOutputExtentFromUser(
            self.iface.mapCanvas().extent(), QgsProject.instance().crs()
        )
        # self.extent_group_box.setOriginalExtnt()
        # Set up things for context help
        self.help_button = self.button_box.button(QDialogButtonBox.Help)
        # Allow toggling the help button
        self.help_button.setCheckable(True)
        self.help_button.toggled.connect(self.help_toggled)

        # Close button action (save state on close)
        self.button_box.button(QDialogButtonBox.Close).clicked.connect(
            self.close
        )
        self.button_box.accepted.connect(self.accept)

        self.button_box.button(QDialogButtonBox.Cancel).setEnabled(False)

        # Used by ffmpeg and convert to set the fps for rendered videos
        self.framerate_spin.setValue(
            int(
                setting(
                    key="frames_per_second",
                    default="90",
                    prefer_project_setting=True,
                )
            )
        )
        # How many frames to render for each feature pair transition
        # The output is generated at e.g. 30fps so choosing 30
        # would fly to each feature for 1s
        # You can then use the 'current_feature' project variable
        # to determine the current feature id
        # and the 'feature_frame' project variable to determine
        # the frame number for the current feature based on frames_for_interval

        self.feature_frames_spin.setValue(
            int(
                setting(
                    key="frames_per_feature",
                    default="90",
                    prefer_project_setting=True,
                )
            )
        )

        # How many frames to dwell at each feature for (output at e.g. 30fps)
        self.hover_frames_spin.setValue(
            int(
                setting(
                    key="dwell_frames",
                    default="30",
                    prefer_project_setting=True,
                )
            )
        )
        # How many frames to render when we are in static mode
        self.extent_frames_spin.setValue(
            int(
                setting(
                    key="frames_for_extent",
                    default="90",
                    prefer_project_setting=True,
                )
            )
        )
        # Keep the scales the same if you dont want it to zoom in an out
        max_scale = float(
            setting(
                key="max_scale",
                default="10000000",
                prefer_project_setting=True,
            )
        )
        min_scale = float(
            setting(
                key="min_scale",
                default="25000000",
                prefer_project_setting=True,
            )
        )
        self.scale_range.setScaleRange(min_scale, max_scale)
        # We need to set min and max at the same time to prevent
        # the scale widget from overriding our preferred values
        self.last_preview_image = None

        # Note: self.pan_easing_widget and zoom_easing_preview are
        # custom widgets implemented in easing_preview.py
        # and added in designer as promoted widgets.
        self.pan_easing_widget.set_checkbox_label("Enable Pan Easing")
        pan_easing_name = setting(
            key="pan_easing", default="Linear", prefer_project_setting=True
        )
        self.pan_easing_widget.set_preview_color("#ffff00")
        self.pan_easing_widget.set_easing_by_name(pan_easing_name)
        if (
            int(
                setting(
                    key="enable_pan_easing",
                    default=0,
                    prefer_project_setting=True,
                )
            )
            == 0
        ):
            self.pan_easing_widget.disable()
        else:
            self.pan_easing_widget.enable()

        self.zoom_easing_widget.set_checkbox_label("Enable Zoom Easing")
        zoom_easing_name = setting(
            key="zoom_easing", default="Linear", prefer_project_setting=True
        )
        self.zoom_easing_widget.set_preview_color("#0000ff")
        self.zoom_easing_widget.set_easing_by_name(zoom_easing_name)
        if (
            int(
                setting(
                    key="enable_zoom_easing",
                    default=0,
                    prefer_project_setting=True,
                )
            )
            == 0
        ):
            self.zoom_easing_widget.disable()
        else:
            self.zoom_easing_widget.enable()

        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), "frames_per_feature", 0
        )
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), "current_frame_for_feature", 0
        )
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), "dwell_frames_per_feature", 0
        )
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), "current_feature_id", 0
        )
        # None, Panning, Hovering
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), "current_animation_action", "None"
        )

        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), "current_frame", "None"
        )
        QgsExpressionContextUtils.setProjectVariable(
            QgsProject.instance(), "total_frame_count", "None"
        )

        mode_string = setting(
            key="map_mode", default="sphere", prefer_project_setting=True
        )
        if mode_string == "sphere":
            self.radio_sphere.setChecked(True)
            self.settings_stack.setCurrentIndex(0)
        elif mode_string == "planar":
            self.radio_planar.setChecked(True)
            self.settings_stack.setCurrentIndex(0)
        else:
            self.radio_extent.setChecked(True)
            self.settings_stack.setCurrentIndex(1)

        self.radio_planar.toggled.connect(self.show_non_fixed_extent_settings)
        self.radio_sphere.toggled.connect(self.show_non_fixed_extent_settings)
        self.radio_extent.toggled.connect(self.show_fixed_extent_settings)

        self.current_preview_frame_render_job = None
        # Set an initial image in the preview based on the current map
        self.show_preview_for_frame(0)

        self.progress_bar.setValue(0)

        self.reuse_cache.setChecked(False)

        # Video playback stuff - see bottom of file for related methods
        self.media_player = QMediaPlayer(
            None, QMediaPlayer.VideoSurface  # .video_preview_widget,
        )
        video_widget = QVideoWidget()
        # self.video_page.replaceWidget(self.video_preview_widget,video_widget)
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.play)
        self.media_player.setVideoOutput(video_widget)
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.error.connect(self.handle_video_error)
        layout = QGridLayout(self.video_preview_widget)
        layout.addWidget(video_widget)
        # Enable options page on startup
        self.main_stack.setCurrentIndex(0)
        # Enable easing status page on startup
        self.render_queue.status_changed.connect(self.show_status)
        self.render_queue.processing_completed.connect(
            self.processing_completed
        )
        self.render_queue.status_message.connect(self.show_message)
        self.render_queue.image_rendered.connect(self.load_image)

        self.movie_task = None

        self.preview_frame_spin.valueChanged.connect(
            self.show_preview_for_frame
        )

        self.register_data_defined_button(
            self.scale_min_dd_btn, AnimationController.PROPERTY_MIN_SCALE
        )
        self.register_data_defined_button(
            self.scale_max_dd_btn, AnimationController.PROPERTY_MAX_SCALE
        )

    def close(self):
        self.save_state()
        self.reject()

    def closeEvent(self, event):
        self.save_state()
        self.reject()

    def _layer_changed(self, layer):
        """
        Triggered when the layer is changed
        """
        self.expression_context_generator.set_layer(layer)

        buttons = self.findChildren(QgsPropertyOverrideButton)
        for button in buttons:
            button.setVectorLayer(layer)

    def register_data_defined_button(self, button, property_key: int):
        """
        Registers a new data defined button, linked to the given property key (see values in AnimationController)
        """
        button.init(
            property_key,
            self.data_defined_properties,
            AnimationController.DYNAMIC_PROPERTIES,
            None,
            False,
        )
        button.changed.connect(self._update_property)
        button.registerExpressionContextGenerator(
            self.expression_context_generator
        )
        button.setVectorLayer(self.layer_combo.currentLayer())

    def _update_property(self):
        """
        Triggered when a property override button value is changed
        """
        button = self.sender()
        self.data_defined_properties.setProperty(
            button.propertyKey(), button.toProperty()
        )

    def update_data_defined_button(self, button):
        """
        Updates the current state of a property override button to reflect the current
        property value
        """
        if button.propertyKey() < 0:
            return

        button.blockSignals(True)
        button.setToProperty(
            self.data_defined_properties.property(button.propertyKey())
        )
        button.blockSignals(False)

    def show_message(self, message):
        self.output_log_text_edit.append(message)

    def show_non_fixed_extent_settings(self):

        self.settings_stack.setCurrentIndex(0)

    def show_fixed_extent_settings(self):

        self.settings_stack.setCurrentIndex(1)

    def show_status(self):
        """
        Display the size of the QgsTaskManager queue.

        :returns: None
        """
        self.active_lcd.display(self.render_queue.active_queue_size())
        self.total_tasks_lcd.display(self.render_queue.total_queue_size)
        self.remaining_features_lcd.display(
            self.render_queue.total_feature_count
            - self.render_queue.completed_feature_count
        )
        self.completed_tasks_lcd.display(self.render_queue.total_completed)
        self.completed_features_lcd.display(
            self.render_queue.completed_feature_count
        )

        self.progress_bar.setValue(self.render_queue.total_completed)

    def set_output_name(self):
        # Popup a dialog to request the filename if scenario_file_path = None
        dialog_title = "Save video"
        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        ok_button.setText("Run")
        ok_button.setEnabled(False)

        output_directory = os.path.dirname(self.movie_file_edit.text())
        if not output_directory:
            output_directory = self.work_directory

        # noinspection PyCallByClass,PyTypeChecker
        file_path, __ = QFileDialog.getSaveFileName(
            self,
            dialog_title,
            os.path.join(output_directory, "qgis_animation.mp4"),
            "Video (*.mp4);;GIF (*.gif)",
        )
        if file_path is None or file_path == "":
            ok_button.setEnabled(False)
            return
        ok_button.setEnabled(True)
        self.movie_file_edit.setText(file_path)

    def choose_music_file(self):
        # Popup a dialog to request the filename for music backing track
        dialog_title = "Music for video"

        # noinspection PyCallByClass,PyTypeChecker
        file_path, __ = QFileDialog.getOpenFileName(
            self,
            dialog_title,
            self.music_file_edit.text(),
            "Mp3 (*.mp3);;Wav (*.wav)",
        )
        if file_path is None or file_path == "":
            return
        self.music_file_edit.setText(self.music_file)

    def save_state(self):
        """
        We save some project settings to both QSettings AND the current project, others just to the current project,
        others just to settings...
        """
        set_setting(
            key="frames_per_second",
            value=self.framerate_spin.value(),
            store_in_project=True,
        )

        if self.radio_sphere.isChecked():
            set_setting(key="map_mode", value="sphere", store_in_project=True)
        elif self.radio_planar.isChecked():
            set_setting(key="map_mode", value="planar", store_in_project=True)
        else:
            set_setting(
                key="map_mode", value="fixed_extent", store_in_project=True
            )
        set_setting(
            key="frames_per_feature",
            value=self.feature_frames_spin.value(),
            store_in_project=True,
        )
        set_setting(
            key="dwell_frames",
            value=self.hover_frames_spin.value(),
            store_in_project=True,
        )
        set_setting(
            key="frames_for_extent",
            value=self.extent_frames_spin.value(),
            store_in_project=True,
        )
        set_setting(
            key="max_scale",
            value=str(self.scale_range.maximumScale()),
            store_in_project=True,
        )
        set_setting(
            key="min_scale",
            value=str(self.scale_range.minimumScale()),
            store_in_project=True,
        )
        set_setting(
            key="enable_pan_easing",
            value=1 if self.pan_easing_widget.is_enabled() else 0,
            store_in_project=True,
        )
        set_setting(
            key="enable_zoom_easing",
            value=1 if self.zoom_easing_widget.is_enabled() else 0,
            store_in_project=True,
        )
        set_setting(
            key="pan_easing",
            value=self.pan_easing_widget.easing_name() or "Linear",
            store_in_project=True,
        )
        set_setting(
            key="zoom_easing",
            value=self.zoom_easing_widget.easing_name() or "Linear",
            store_in_project=True,
        )
        set_setting(
            key="output_file",
            value=self.movie_file_edit.text(),
            store_in_project=True,
        )
        set_setting(
            key="music_file",
            value=self.music_file_edit.text(),
            store_in_project=True,
        )

        # only saved to project
        if self.layer_combo.currentLayer():
            QgsProject.instance().writeEntry(
                "animation", "layer_id", self.layer_combo.currentLayer().id()
            )
        else:
            QgsProject.instance().removeEntry("animation", "layer_id")
        temp_doc = QDomDocument()
        dd_elem = temp_doc.createElement("data_defined_properties")
        self.data_defined_properties.writeXml(
            dd_elem, AnimationController.DYNAMIC_PROPERTIES
        )
        temp_doc.appendChild(dd_elem)
        QgsProject.instance().writeEntry(
            "animation", "data_defined_properties", temp_doc.toString()
        )

    # Prevent the slot being called twize
    @pyqtSlot()
    def accept(self):
        """Process the animation sequence.

        .. note:: This is called on OK click.
        """
        # Enable progress page on startup
        self.main_stack.setCurrentIndex(1)
        # Image preview page
        self.preview_stack.setCurrentIndex(0)
        # Enable queue status page
        # set parameter from dialog

        if not self.reuse_cache.isChecked():
            os.system(
                "rm %s/%s*" % (self.work_directory, self.frame_filename_prefix)
            )

        self.save_state()
        self.run_frame.show()

        self.render_queue.reset()
        self.last_preview_image = None
        self.output_log_text_edit.clear()
        self.output_log_text_edit.append(
            "Preparing animation run. Please wait."
        )
        controller = self.create_controller()
        if not controller:
            return

        controller.reuse_cache = self.reuse_cache.isChecked()

        self.render_queue.set_annotations(
            QgsProject.instance().annotationManager().annotations()
        )
        self.render_queue.set_decorations(self.iface.activeDecorations())

        self.output_log_text_edit.append(
            "Generating {} frames".format(controller.total_frame_count)
        )
        self.progress_bar.setMaximum(controller.total_frame_count)
        self.progress_bar.setValue(0)

        def log_message(message):
            self.output_log_text_edit.append(message)

        controller.normal_message.connect(log_message)
        if int(setting(key="verbose_mode", default=0)):
            controller.verbose_message.connect(log_message)

        self.render_queue.total_feature_count = controller.total_feature_count
        self.render_queue.frames_per_feature = (
            controller.travel_frames + controller.dwell_frames
        )

        for image_counter, job in enumerate(controller.create_jobs()):
            self.output_log_text_edit.append(job.file_name)
            self.render_queue.add_job(job)

        self.button_box.button(QDialogButtonBox.Cancel).setEnabled(True)
        # Now all the tasks are prepared, start the render_queue processing
        self.render_queue.start_processing()

    def cancel_processing(self):
        self.button_box.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.render_queue.cancel_processing()
        # Enable progress page
        self.main_stack.setCurrentIndex(0)

    def create_controller(self) -> Optional[AnimationController]:
        """
        Creates a new animation controller based on the state of the dialog
        """
        if self.radio_sphere.isChecked():
            map_mode = MapMode.SPHERE
        elif self.radio_planar.isChecked():
            map_mode = MapMode.PLANAR
        else:
            map_mode = MapMode.FIXED_EXTENT

        if map_mode != MapMode.FIXED_EXTENT:
            if not self.layer_combo.currentLayer():
                self.output_log_text_edit.append(
                    "Cannot generate sequence without choosing a layer"
                )
                return

            layer_type = qgis.core.QgsWkbTypes.displayString(
                int(self.layer_combo.currentLayer().wkbType())
            )
            layer_name = self.layer_combo.currentLayer().name()
            self.output_log_text_edit.append(
                "Generating flight path for %s layer: %s"
                % (layer_type, layer_name)
            )

        if map_mode == MapMode.FIXED_EXTENT:
            controller = AnimationController.create_fixed_extent_controller(
                map_settings=self.iface.mapCanvas().mapSettings(),
                feature_layer=self.layer_combo.currentLayer() or None,
                output_extent=QgsReferencedRectangle(
                    self.extent_group_box.outputExtent(),
                    self.extent_group_box.outputCrs(),
                ),
                total_frames=self.extent_frames_spin.value(),
                frame_rate=self.framerate_spin.value(),
            )
        else:
            try:
                controller = (
                    AnimationController.create_moving_extent_controller(
                        map_settings=self.iface.mapCanvas().mapSettings(),
                        mode=map_mode,
                        feature_layer=self.layer_combo.currentLayer(),
                        travel_frames=self.feature_frames_spin.value(),
                        dwell_frames=self.hover_frames_spin.value(),
                        min_scale=self.scale_range.minimumScale(),
                        max_scale=self.scale_range.maximumScale(),
                        pan_easing=self.pan_easing_widget.get_easing()
                        if self.pan_easing_widget.is_enabled()
                        else None,
                        zoom_easing=self.zoom_easing_widget.get_easing()
                        if self.zoom_easing_widget.is_enabled()
                        else None,
                        frame_rate=self.framerate_spin.value(),
                    )
                )
            except InvalidAnimationParametersException as e:
                self.output_log_text_edit.append(f"Processing halted: {e}")
                return None

        controller.data_defined_properties = QgsPropertyCollection(
            self.data_defined_properties
        )
        return controller

    def processing_completed(self, success: bool):
        """Run after all processing is done to generate gif or mp4.

        .. note:: This called by process_more_tasks when all tasks are complete.
        """
        if not success:
            self.output_log_text_edit.append("Canceled by user")
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(0)
            self.button_box.button(QDialogButtonBox.Cancel).setEnabled(False)
            return

        self.movie_task = MovieCreationTask(
            output_file=self.movie_file_edit.text(),
            music_file=self.music_file_edit.text(),
            output_format=MovieFormat.GIF
            if self.radio_gif.isChecked()
            else MovieFormat.MP4,
            work_directory=self.work_directory,
            frame_filename_prefix=self.frame_filename_prefix,
            framerate=self.framerate_spin.value(),
        )

        def log_message(message):
            self.output_log_text_edit.append(message)

        def show_movie(movie_file: str):
            # Video preview page
            self.main_stack.setCurrentIndex(1)
            self.preview_stack.setCurrentIndex(1)
            self.media_player.setMedia(
                QMediaContent(QUrl.fromLocalFile(movie_file))
            )
            self.play_button.setEnabled(True)
            self.play()

        def cleanup_movie_task():
            self.movie_task = None

            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(0)

        self.movie_task.message.connect(log_message)
        self.movie_task.movie_created.connect(show_movie)

        # todo - show a message based on success/fail
        self.movie_task.taskCompleted.connect(cleanup_movie_task)
        self.movie_task.taskTerminated.connect(cleanup_movie_task)

        QgsApplication.taskManager().addTask(self.movie_task)

        self.button_box.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.main_stack.setCurrentIndex(0)

    def show_preview_for_frame(self, frame: int):
        if self.radio_sphere.isChecked() or self.radio_planar.isChecked():
            if not self.layer_combo.currentLayer():
                self.output_log_text_edit.append(
                    "Cannot generate sequence without choosing a layer"
                )
                return
        if self.current_preview_frame_render_job:
            self.current_preview_frame_render_job.cancel()
            self.current_preview_frame_render_job = None

        controller = self.create_controller()
        job = controller.create_job_for_frame(frame)
        if not job:
            return

        def update_preview_image(file_name):
            if not self.current_preview_frame_render_job:
                return

            image = QImage(file_name)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                self.current_frame_preview.setPixmap(pixmap)

            self.current_preview_frame_render_job = None

        job.file_name = "/tmp/tmp_image.png"
        self.current_preview_frame_render_job = job.create_task()

        self.current_preview_frame_render_job.taskCompleted.connect(
            partial(update_preview_image, file_name=job.file_name)
        )
        self.current_preview_frame_render_job.taskTerminated.connect(
            partial(update_preview_image, file_name=job.file_name)
        )

        QgsApplication.taskManager().addTask(
            self.current_preview_frame_render_job
        )

    def load_image(self, name):
        if (
            self.last_preview_image is not None
            and self.last_preview_image > name
        ):
            # Images won't necessarily be rendered in order, so only update the
            # preview image if the rendered image is from later in the animation
            # vs the one we are currently showing. Avoids the preview jumping
            # forward and backward and zooming/in out in unpredictable patterns
            return

        self.last_preview_image = name
        # Load the preview with the named image file
        try:
            with open(name, "rb") as image_file:
                content = image_file.read()
                image = QImage()
                image.loadFromData(content)
                pixmap = QPixmap.fromImage(image)
                self.current_frame_preview.setPixmap(pixmap)
        except:
            pass

    def help_toggled(self, flag):
        """Show or hide the help tab in the stacked widget.
        :param flag: Flag indicating whether help should be shown or hidden.
        :type flag: bool
        """
        if flag:
            self.help_button.setText(self.tr("Hide Help"))
            self.show_help()
        else:
            self.help_button.setText(self.tr("Show Help"))
            self.hide_help()

    def hide_help(self):
        """Hide the usage info from the user."""
        self.main_stacked_widget.setCurrentIndex(1)

    def show_help(self):
        """Show usage info to the user."""
        # Read the header and footer html snippets
        self.main_stacked_widget.setCurrentIndex(0)
        header = html_header()
        footer = html_footer()

        string = header

        message = workbench_help()

        string += message.to_html()
        string += footer

        self.help_web_view.setHtml(string)

    # Video Playback Methods
    def play(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def media_state_changed(self, state):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause)
            )
        else:
            self.play_button.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay)
            )

    def position_changed(self, position):
        self.video_slider.setValue(position)

    def duration_changed(self, duration):
        self.video_slider.setRange(0, duration)

    def set_position(self, position):
        self.media_player.setPosition(position)

    def handle_video_error(self):
        self.play_button.setEnabled(False)
        self.output_log_text_edit.append(self.media_player.errorString())
